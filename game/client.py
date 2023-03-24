import json
import threading
from game.models.player import Player
from game.models.action import Action
from game.lobby.tracker import Tracker
from game.models.vote import Vote
from game.thread_manager import ThreadManager
from game.transport.transport import Transport
from game.transport.packet import AckStart, Nak, Ack, PeeringCompleted, Packet, ReadyToStart, SatDown
import config
import keyboard
import game.clock.sync as sync 
from time import time, sleep


class Client():
    """
    Game FSM
    """

    def __init__(self, my_name: str, tracker: Tracker, host_socket=None):
        super().__init__()

        self._state: str = "PEERING"
        self._myself = Player(name=my_name)
        self.game_over = False
        self.tracker = tracker
        self.host_socket = host_socket  # for testing only
        

        self.lock = threading.Lock()

        self._players: dict[str, Player] = {
            self._myself.get_name(): self._myself}
        self._votekick: dict[str, int] = {}
        self._round_inputs: dict[int, str] = {
            # Q W E R T Y = 12, 13, 14, 15, 17, 16
            12: None,
            # 13: None,
            # 14: None,
            # 15: None,
            # 17: None,
            # 16: None,
        }

        self.hotkeys_added = False
        self._round_started = False
        self._round_ready = {}
        self._round_ackstart = {}
        self._sat_down_count = 0

        self._current_chairs: int = config.NUM_CHAIRS
        self._my_keypress = None

        # selecting seats algo
        self._nak_count = 0
        self._ack_count = 0
        self._is_selecting_seat = False
        self._done_voting = False

        # transport layer stuff
        self._transportLayer = Transport(my_name,
                                         self.tracker.get_ip_port(my_name)[1],
                                         ThreadManager(),
                                         tracker=self.tracker,
                                         host_socket=host_socket)
        self.is_peering_completed = False
        self._sync = sync.Sync(self.tracker, self._transportLayer, self._myself)

    def _state(self):
        return self._state

    def start(self):
        print("Game has started!")
        try:
            while not self.game_over:
                sleep(0.5)  # slow down game loop
                self.trigger_handler(self._state)
        except KeyboardInterrupt:
            print("Exiting game")
            self._transportLayer.shutdown()

    def trigger_handler(self, state):
        if state == "PEERING":
            self.peering()

        if state == "SYNCHRONIZE_CLOCK":
            self.sync_clock()

        if state == "INIT":
            self.init()

        elif state == "AWAIT_KEYPRESS":
            self.await_keypress()

        elif state == "AWAIT_ROUND_END":
            self.await_round_end()

        elif state == "BYZANTINE_SEND":
            self.byzantine_send()

        elif state == "BYZANTINE_RECV":
            self.byzantine_recv()

        elif state == "END_ROUND":
            self.end_round()

        elif state == "END_GAME":
            self.end_game()

    def peering(self):
        print(self._transportLayer.get_connection_pool())
        if self._transportLayer.all_connected() and not self.is_peering_completed:
            print("Connected to all peers")
            print("Notify peers that peering is completed")
            self._transportLayer.sendall(PeeringCompleted(player=self._myself))
            self.is_peering_completed = True
            self._state = "SYNCHRONIZE_CLOCK"

    def sync_clock(self):
        while self._sync.leader_idx != len(self._sync.leader_list)-1:
            self._sync.sync_state_checker() # Control Flow Moves to Check_Leader Function
        print("self._sync.leader_idx != len(self._sync.leader_list)-1")


        #If the condition is met
        self._sync.leader_idx = 0
        # If self.leader_idx == len(self.leader_list)-1 you move into Game Play
        self._state = "INIT"

    def init(self):
        # we only reach here once peering is completed
        # everybody sends ok start to everyone else
        self._transportLayer.sendall(ReadyToStart(self._myself))
        self._checkTransportLayerForIncomingData()
        if len(self._round_ready.keys()) == len(self._round_inputs) - 1:
            print("All players are ready to start.")
            print("Voting to start now...")
            self._transportLayer.sendall(AckStart(self._myself))
            # self._round_inputs = { k:None for k in range(12, 12 + len(self._players) -1) }
            self._state = "AWAIT_KEYPRESS"

    def await_keypress(self):
        self._checkTransportLayerForIncomingData()
        if not self._all_voted_to_start():
            # waiting for everyone to ackstart
            return

        if not self._round_started:
            self._round_started = True
            # print("All have voted to start...")
            # print("Let's begin!")
            # print("Good luck and have fun!")
            print(f"\n---- Available seats: {self._round_inputs} ----")
            print(f"Current players: {self._players.keys()}")
            print("Grab a seat now!")

        if self._round_started:
            # 1) Received local keypress
            if self._my_keypress is None:
                if not self.hotkeys_added:
                    for k in self._round_inputs.keys():
                        ## FOR TESTING ONLY ##
                        # host takes Q and client takes W
                        if not self.host_socket and k == 12:
                            continue
                        if self.host_socket and k == 13:
                            continue
                        keyboard.add_hotkey(
                            k, self._insert_input, args=(k,))
                        self.hotkeys_added = True

            elif not self._is_selecting_seat:
                # first time we've received a keypress, and have yet to enter selecting seat
                self._selecting_seats()

            if self._is_selecting_seat:
                thresh = 1  # (len(self._round_inputs)) // 2
                if (self._nak_count + self._ack_count) == len(self._round_inputs)-1:
                    if self._nak_count >= thresh:
                        # SelectingSeat failed
                        self._my_keypress = None
                        self._nak_count = 0
                        self._ack_count = 0
                        self._is_selecting_seat = False
                        self.hotkeys_added = False
                    else:
                        # SelectingSeat success
                        self.lock.acquire()
                        self._round_inputs[self._my_keypress] = self._myself.get_name(
                        )
                        self.lock.release()
                        self._transportLayer.sendall(SatDown(self._myself))
                        self._sat_down_count += 1
                        self._state = "AWAIT_ROUND_END"
                        return

            # if everyone else has sat down, move onto next state
            elif self._sat_down_count >= len(self._round_inputs.keys()):
                self._state = "AWAIT_ROUND_END"

        # 4) Check for others' keypress, let transport layer handler handle it
        # self._checkTransportLayerForIncomingData()

    def await_round_end(self):
        print("Waiting for all votes to come in...")
        self._checkTransportLayerForIncomingData()
        if self._sat_down_count >= len(self._round_inputs.keys()):
            # everyone is ready to vote
            if not self._done_voting:
                print(
                    f"preparing to vote, current inputs: {self._round_inputs}")
                print(f"preparing to vote, current players: {self._players}")
                # choosing who to kick
                player_to_kick = None
                for playerid in self._players.keys():
                    if playerid not in self._round_inputs.values():
                        player_to_kick = playerid
                        print(
                            f"Sending vote to kick player: {self._players[playerid].get_name()}")
                        packet = Vote(player_to_kick, self._myself)
                        self._transportLayer.sendall(packet)
                        # my own vote
                        # TODO: might need to change; player might be assigning vote after it has received votes
                        numvotes = self._votekick.get(player_to_kick, 0)
                        self._votekick[player_to_kick] = numvotes + 1
                        break  # break after the first player to kick
                self._done_voting = True

                if player_to_kick == None:
                    print("Cannot find player to kick, moving to next round")
                    self._state = "END_ROUND"
                    return

            # tallying votes
            else:
                print(f"i have voted. Waiting for votes: {self._votekick}")
                if sum(self._votekick.values()) == len(self._players):
                    print("all votes in")
                    max_vote = max(self._votekick.values())
                    print(f"votekick dict: {self._votekick}")
                    # in case there is a tie
                    to_be_kicked = [key for key,
                                    value in self._votekick.items() if value == max_vote]

                    print(f"tobekicked = {to_be_kicked}")
                    # 1) if only one voted, remove from player_list
                    if len(to_be_kicked) == 1:
                        print(f"Kicking player: {to_be_kicked[0]}")
                        self._players.pop(to_be_kicked[0])

                    else:
                        print(
                            "Vote tied; moving onto the next round with nobody kicked")

                    self._state = "END_ROUND"

    def end_round(self):
        # clear all variables
        print(
            f"\n---- Round has ended. Players left: {self._players.keys()} ----")
        sleep(5)
        self._reset_round()

        # if no chairs left, end the game, else reset
        if len(self._round_inputs.keys()) < 1:
            print("No more seats left, ending game!")
            self._transportLayer.shutdown()
            self._state = "END_GAME"
        else:
            # must wait for everyone to signal end round before moving on to next round
            self._state = "AWAIT_KEYPRESS"

    def end_game(self):
        # terminate all connectionsidk
        self._transportLayer.shutdown()
        self.game_over = True


######### helper functions #########

    def _checkTransportLayerForIncomingData(self):
        """handle data being received from transport layer"""
        pkt: Packet = self._transportLayer.receive()

        if pkt:
            if pkt.get_packet_type() == "action":
                # keypress
                self._receiving_seats(pkt)

            elif pkt.get_packet_type() == "ss_nak":
                # drop the nak/ack if we've moved on
                if self._is_selecting_seat:
                    self._nak_count += 1

            elif pkt.get_packet_type() == "ss_ack":
                # drop the nak/ack if we've moved on
                if self._is_selecting_seat:
                    self._ack_count += 1

            elif pkt.get_packet_type() == "peering_completed":
                print(
                    f"Received peering completed from {pkt.get_player().get_name()}")

            elif pkt.get_packet_type() == "ready_to_start":
                player_name = pkt.get_player().get_name()
                self._round_ready[player_name] = True
                self._players[player_name] = Player(player_name)
                print(f"Received ready to start from {player_name}")

            elif pkt.get_packet_type() == "ack_start":
                player_name = pkt.get_player().get_name()
                self._round_ackstart[player_name] = True
                print(f"Received vote to start from {player_name}")

            elif pkt.get_packet_type() == "ack":
                player_name = pkt.get_player().get_name()
                self._ack_count += 1
                print(f"Received ack to sit from {player_name}")

            elif pkt.get_packet_type() == "nak":
                player_name = pkt.get_player().get_name()
                self._nak_count += 1
                print(f"Received nak to sit from {player_name}")

            elif pkt.get_packet_type() == "sat_down":
                player_name = pkt.get_player().get_name()
                self._sat_down_count += 1
                print(f"Received {player_name} has sat down")

            elif pkt.get_packet_type() == "vote":
                player_to_kick = pkt.get_data()
                print(f"receiving data: {player_to_kick}")
                if player_to_kick in self._votekick:
                    self._votekick[player_to_kick] += 1
                else:
                    self._votekick[player_to_kick] = 1

                print(f"Updated votekick table: {self._votekick}")

    def _all_voted_to_start(self):
        return len(self._round_ackstart.keys()) >= len(self._round_inputs)-1

    def _selecting_seats(self):
        self._is_selecting_seat = True
        pkt = Action(dict(seat=self._my_keypress), self._myself)
        self._transportLayer.sendall(pkt)

    def _send_ack(self, player: Player):
        self._transportLayer.send(Ack(self._myself), player.get_name())

    def _send_nak(self, player: Player):
        self._transportLayer.send(Nak(self._myself), player.get_name())

    def _next(self):
        self._state = self.trigger_handler(self._state)
        return self._state

    def _insert_input(self, keypress):
        print(keypress)
        self._my_keypress = keypress
        keyboard.remove_all_hotkeys()

    def _receiving_seats(self, action: Packet):
        seat = action.get_data().get("seat")
        player = action.get_player()
        if seat:
            print(f"Received seat: {seat} from {player}")
            self.lock.acquire()
            if self._round_inputs[seat] is not None:
                print(4)
                self._send_nak(player)
                self.lock.release()
                return
            self._round_inputs[seat] = player.get_name()
            self._send_ack(player)
            self.lock.release()
            print(self._round_inputs)
            return

    def _reset_round(self):
        # TODO: SAVE TO LOGS
        print("Clearing round data...")
        # init
        self._round_ready = {}
        self._round_ackstart = {}
        self._round_started = False

        # reset round inputs, num chairs - 1
        print("Reducing number of chairs...")
        d = self._round_inputs
        d = {key: None for key in d}
        d.popitem()
        self._round_inputs = d

        #
        self._my_keypress = None
        self._nak_count = 0
        self._ack_count = 0
        self._is_selecting_seat = False
        self.hotkeys_added = False

        self._sat_down_count = 0
        self._votekick = {}
        self._done_voting = False
