import json
import threading
from game.clock.clock import Clock
from game.models.player import Player
from game.models.action import Action
from game.lobby.tracker import Tracker
from game.models.vote import Vote
from game.thread_manager import ThreadManager
from game.transport.transport import Transport
from game.transport.packet import AckStart, EndGame, Nak, Ack, PeeringCompleted, Packet, ReadyToStart, SatDown, FrameSync
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
        self.my_ip, self.my_port_number = self.tracker.get_ip_port(
            self._myself.get_name())  # for testing only
        
        self._tracker_list = self.tracker.get_tracker_list()
        self._total_players = self.tracker.get_player_count()

        self.lock = threading.Lock()

        self._players: dict[str, Player] = {
            self._myself.get_name(): self._myself}
        self._votekick: dict[str, int] = {}

        # Initialise round inputs to num of players - 1
        KEYBOARD_MAPPING = [12, 13, 14, 15, 17, 16]
        self._round_inputs = {k: None for k in [
            config.KEYBOARD_MAPPING[i] for i in range(self._total_players - 1)]}

        self.frame_count = 0

        self.hotkeys_added = False
        self._round_started = False
        self._round_ready = {}
        self._round_ackstart = {}
        self._sat_down_count = 0

        self._vote_tied = False

        self._my_keypress = None
        self._my_keypress_time = None
        self._last_sent_ready_to_start = None

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
        print(f"Tracker_List Before Sync:{self.tracker.get_tracker_list()}")
        print(
            f"Leader List Before Sync Initialisation:{self.tracker.get_leader_list()}")

        self._frameSync = Clock(
            self._myself, self._transportLayer, self._myself if host_socket else None)

        self.is_peering_completed = False
        self.is_sync_complete = False

    def _state(self):
        return self._state

    def start(self):
        print("Game has started!")
        try:
            while not self.game_over:
                sleep(1)  # slow down game loop
                self.frame_count += 1
                # if self.frame_count % 10 == 0:
                #     self._transportLayer.sendall(
                #         FrameSync(self.frame_count, self._myself))
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

        elif state == "END_ROUND":
            self.end_round()

        elif state == "END_GAME":
            self.end_game()

        elif state == "SPECTATOR":
            self.spectator()

        elif state == "FINAL_ROUND":
            self.final_round()

    def peering(self):
        print('In Peering')
        # print(self._transportLayer.get_connection_pool())

        if self._transportLayer.all_connected() and not self.is_peering_completed:
            print("Connected to all peers")
            print("Notify peers that peering is completed")
            self._transportLayer.sendall(PeeringCompleted(player=self._myself))
            self.is_peering_completed = True
            self._transportLayer.reset_sync()
            self._state = "SYNCHRONIZE_CLOCK"

    def sync_clock(self):
        print("syncing")
        while not self.is_sync_complete:
            # Control Flow Moves to Check_Leader Function
            self.is_sync_complete = self._transportLayer.syncing()
            sleep(1)
        # If self.leader_idx == len(self.leader_list)-1 you move into Game Play
        self._state = "INIT"

    def init(self):
        # we only reach here once peering is completed
        # everybody sends ok start to everyone else
        self._checkTransportLayerForIncomingData()

        if len(self._round_ready.keys()) < self._total_players - 1:
            if self._last_sent_ready_to_start is None or time() - self._last_sent_ready_to_start > 3:
                self._last_sent_ready_to_start = time()
                self._frameSync.if_master_emit_new_master(self._myself)
                self._transportLayer.sendall(ReadyToStart(self._myself))
        else:
            print("All players are ready to start.")
            print("Voting to start now...")
            self._transportLayer.sendall(AckStart(self._myself))

            if self._all_voted_to_start():
                # waiting for everyone to ackstart
                self._state = "AWAIT_KEYPRESS"
                return

    def await_keypress(self):
        self._checkTransportLayerForIncomingData()

        if not self._round_started:
            self._round_started = True
            print(f"\n---- Available seats: {self._round_inputs} ----")
            print(f"Current players: {self._players.keys()}")
            print("Grab a seat now!")

        if self._round_started:
            # 1) Received local keypress
            if self._my_keypress is None:
                if not self.hotkeys_added:
                    for k in self._round_inputs.keys():
                        ## FOR TESTING ONLY ##
                        # player takes hotkey sequentially accordingly to port number
                        # port 9999 takes 12, 10000 takes 13...
                        # if not (k + 9987 == self.my_port_number):
                        #     continue
                        keyboard.add_hotkey(
                            k, self._insert_input, args=(k,))
                        self.hotkeys_added = True

            elif not self._is_selecting_seat:
                # first time we've received a keypress, and have yet to enter selecting seat
                self._selecting_seats()

            if self._is_selecting_seat:
                thresh = len(self._players) // 2
                if (self._nak_count + self._ack_count) >= len(self._players)-1:
                    if self._nak_count >= thresh:
                        print("Failed to sit down, pick a new seat!")
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
                        self._transportLayer.sendall(
                            SatDown(self._my_keypress, self._myself))
                        self._sat_down_count += 1
                        print("[ACTION] I have sat down successfully!")
                        print(f"{self._round_inputs}")
                        self._state = "AWAIT_ROUND_END"
                        return

            # if everyone else has sat down, move onto next state
            elif all(self._round_inputs.values()):
                self._state = "AWAIT_ROUND_END"
                # if len(self._round_inputs) > 1:
                #     self._state = "AWAIT_ROUND_END"
                # else:
                #     self._state = "FINAL_ROUND"

    def await_round_end(self):
        self._checkTransportLayerForIncomingData()
        if all(self._round_inputs.values()):
            # everyone is ready to vote
            if not self._done_voting:
                # choosing who to kick
                player_to_kick = None
                for playerid in self._players.keys():
                    if playerid not in self._round_inputs.values():
                        player_to_kick = playerid
                        print(
                            f"[VOTE] Voting to kick: {self._players[playerid].get_name()}")
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
                print(f"Waiting for votes... Current votes: {self._votekick}")
                if sum(self._votekick.values()) >= len(self._players):
                    print("[ALL VOTES IN]")
                    max_vote = max(self._votekick.values())
                    # in case there is a tie
                    to_be_kicked = [key for key,
                                    value in self._votekick.items() if value == max_vote]

                    # 1) if only one voted, remove from player_list
                    if len(to_be_kicked) == 1:
                        print(
                            f"[KICKING LOSER] Kicking player: {to_be_kicked[0]}")
                        self._players.pop(to_be_kicked[0])

                    else:
                        self._vote_tied = True
                        print(
                            "Vote tied; moving onto the next round with nobody kicked")

                    self._state = "END_ROUND"

    def end_round(self):
        # clear all variables
        print(
            f"\n---- Round has ended. Players left: {list(self._players.keys())} ----")
        sleep(5)
        self._reset_round()

        # player has lost the game
        if not self._players.get(self._myself.get_name(), None):
            print("You lost! Enjoy spectating the game!")
            self._state = "SPECTATOR"

        # if no chairs left, end the game, else reset
        elif len(self._round_inputs.keys()) < 1:
            winner = list(self._players.keys())[0]
            print('No more seats left, game over.')
            print(
                f"\n--- {'Congrats! You have' if winner == self._myself.get_name() else winner + ' has'} won the game! ---\n")
            # TODO: last remaining player sends packet to initiate shutdown for players who have already lost
            self._transportLayer.sendall(EndGame(self._myself))
            self._state = "END_GAME"

        else:
            # must wait for everyone to signal end round before moving on to next round
            self._state = "AWAIT_KEYPRESS"

    def end_game(self):
        # terminate all connectionsidk
        self._transportLayer.shutdown()
        self.game_over = True

    def spectator(self):
        # for player who last lost game
        self._checkTransportLayerForIncomingData()

    def final_round(self):
        # for player who last lost game
        self._checkTransportLayerForIncomingData()


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

            elif pkt.get_packet_type() == "peering_completed" and not self._round_started:
                print(
                    f"[Peering Completed] {pkt.get_player().get_name()}")

            elif pkt.get_packet_type() == "ready_to_start" and not self._round_started:
                player_name = pkt.get_player().get_name()
                self._round_ready[player_name] = True
                self._players[player_name] = Player(player_name)
                print(f"[Ready to Start]{player_name}")

            elif pkt.get_packet_type() == "ack_start" and not self._round_started:
                player_name = pkt.get_player().get_name()
                self._round_ackstart[player_name] = True
                print(f"[Vote to Start] {player_name}")

            elif pkt.get_packet_type() == "ack":
                player_name = pkt.get_player().get_name()
                self._ack_count += 1
                print(f"[ACK from] {player_name}")

            elif pkt.get_packet_type() == "nak":
                player_name = pkt.get_player().get_name()
                self._nak_count += 1
                print(f"[NAK from] {player_name}")

            elif pkt.get_packet_type() == "sat_down":
                player_name = pkt.get_player().get_name()
                seat = pkt.get_data()
                self._sat_down_count += 1
                self.lock.acquire()
                self._round_inputs[seat] = player_name
                self.lock.release()
                print(f"[ACTION] {player_name} has sat down!")
                print(f"[SEATS] {self._round_inputs}")

            elif pkt.get_packet_type() == "vote":
                player_to_kick = pkt.get_data()
                print(f"[VOTEKICK] {player_to_kick}")
                if player_to_kick in self._votekick:
                    self._votekick[player_to_kick] += 1
                else:
                    self._votekick[player_to_kick] = 1

                print(f"{self._votekick}")

            elif pkt.get_packet_type() == "sync_req":
                pass

            elif pkt.get_packet_type() == "update_master":
                player = pkt.get_player()
                new_master_name = pkt.get_data()
                if self._frameSync.get_master() is None or player.get_name() == self._frameSync.get_master().get_name():
                    print(
                        f"Updating master to {new_master_name}")
                    self._frameSync.update_master(
                        Player(new_master_name), None)

            elif pkt.get_packet_type() == "acquire_master":
                playerRequestingForMaster = pkt.get_player()
                self._frameSync.if_master_emit_new_master(
                    playerRequestingForMaster)
                self._frameSync.update_master(
                    playerRequestingForMaster, self._myself)

            elif pkt.get_packet_type() == "frame_sync":
                frame = pkt.get_data()
                player = pkt.get_player()
                self._frameSync.update_frame(player.get_name(), frame)
                if self._frameSync.get_master():
                    if self._frameSync.get_master().get_name() == player.get_name():
                        if frame < self.frame_count:
                            print("Slow down since master is behind")
                            sleep(0.3)
                        elif frame > self.frame_count:
                            print("Requesting to be master since I'm behind")
                            self._frameSync.acquire_master()

            elif pkt.get_packet_type() == "end_game":
                winner = pkt.get_player()
                if self._state == "SPECTATOR":
                    print(f"[END GAME] {winner} has won the game!")
                    self._state = "END_GAME"

    def _all_voted_to_start(self):
        return len(self._round_ackstart.keys()) >= len(self._round_inputs)-1

    def _selecting_seats(self):
        self._is_selecting_seat = True
        pkt = Action(dict(seat=self._my_keypress), self._myself)
        self._my_keypress_time = pkt.get_created_at()
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
        created_at = action.get_created_at()
        if seat:
            print(f"Received seat: {seat} from {player}")
            self.lock.acquire()
            if self._round_inputs[seat] is not None:
                self._send_nak(player)
                self.lock.release()
                return
            if len(self._round_inputs) == 1:
                # final round break deadlock
                if self._my_keypress_time is not None:
                    if created_at >= self._my_keypress_time:
                        # if their kp timing >= mine,
                        self._send_nak(player)
                        self.lock.release()
                        return
            self._send_ack(player)
            self._round_inputs[seat] = player.get_name()
            self.lock.release()
            print(self._round_inputs)
            return

    def _reset_round(self):
        print("Clearing round data...")
        # init
        self._round_ready = {}
        self._round_ackstart = {}
        self._round_started = False

        if not self._vote_tied:
            # reset round inputs, num chairs - 1
            print("Reducing number of chairs...")
            d = self._round_inputs
            d = {key: None for key in d}
            d.popitem()
            self._round_inputs = d

        self._my_keypress = None
        self._nak_count = 0
        self._ack_count = 0
        self._is_selecting_seat = False
        self.hotkeys_added = False
        self._sat_down_count = 0
        self._votekick = {}
        self._done_voting = False

        self._vote_tied = False
