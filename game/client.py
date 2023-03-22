from game.models.player import Player
from game.models.action import Action
from game.lobby.tracker import Tracker
from game.thread_manager import ThreadManager
from game.transport.transport import Transport
from game.transport.packet import AckStart, Nak, Ack, PeeringCompleted, Packet, ReadyToStart,
import config
import keyboard
from time import time


class Client():
    """
    Game FSM 
    """

    def __init__(self, my_name: str, tracker: Tracker, host_socket=None):
        super().__init__()

        self._state: str = "PEERING"
        self._players: dict[str, Player] = {}
        self._myself = Player(name=my_name)
        self.game_over = False
        self.tracker = tracker

        self._round_inputs: dict[int, str] = {
            # Q W E R T Y = 12, 13, 14, 15, 17, 16
            12: None,
            13: None,
            14: None,
            15: None,
            17: None,
            16: None,
        }
        self._round_ready = {}
        self._round_ackstart = {}

        self._current_chairs: int = config.NUM_CHAIRS
        self._my_keypress = None

        # selecting seats algo
        self._nak_count = 0
        self._ack_count = 0
        self._is_selecting_seat = False

        # transport layer stuff
        self._transportLayer = Transport(my_name,
                                         self.tracker.get_ip_port(my_name)[1],
                                         ThreadManager(),
                                         tracker=self.tracker,
                                         host_socket=host_socket)
        self.is_peering_completed = False

    def _state(self):
        return self._state

    def start(self):
        try:
            while not self.game_over:
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

        elif state == "PROC_OTHERS_KEYPRESS":
            self.process_others_keypress()

        elif state == "END_ROUND":
            self.end_round

        elif state == "END_GAME":
            self.end_game()

    def peering(self):
        if self._transportLayer.all_connected() and not self.is_peering_completed:
            print("Connected to all peers")
            print("Notifying peering completed")
            self._transportLayer.sendall(PeeringCompleted(player=self._myself))
            self.is_peering_completed = True
            self._state = "INIT"

    def sync_clock(self):
        # logic to sync clocks here
        time.sleep(10)
        self._state = "INIT"

    def init(self):
        # we only reach here once peering is completed
        # everybody sends ok start to everyone else
        self._transportLayer.sendall(ReadyToStart(self._myself))
        
        if len(self._round_ready.keys()) == config.NUM_PLAYERS:
            print("All players are ready to start.")
            print("Voting to start now...")
            self._transportLayer.sendall(AckStart(self._myself))
            self._state = "AWAIT_KEYPRESS"

    def await_keypress(self):
        if len(self._round_ackstart.keys()) >= config.NUM_PLAYERS:
            # waiting for everyone to ackstart
            return
        
        # 1) Received local keypress
        if self._my_keypress is None:
            for k in self._round_inputs.keys():
                keyboard.add_hotkey(k, lambda: self._insert_input(k))
        else:
            # 2) SelectingSeat
            self._selecting_seats()

        if self._is_selecting_seat:
            thresh = (config.NUM_PLAYERS // 2)
            if self._nak_count >= thresh:
                # SelectingSeat failed
                self._my_keypress = None
                self._nak_count = 0
                self._ack_count = 0
                self._is_selecting_seat = False

            if self._ack_count > thresh:
                # SelectingSeat success
                self._state("END_ROUND")
                self._next()
                return

        # 4) Check for others' keypress, let transport layer handler handle it
        self._checkTransportLayerForIncomingData()

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
                p = Player(pkt.get_player().get_name())
                action = Action(pkt.get_data(), p)
                self._receiving_seats(action)

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
                print(f"Received ready to start from {player_name}")
            elif pkt.get_packet_type() == "ack_start":
                player_name = pkt.get_player().get_name()
                self._round_ackstart[player_name] = True
                print(f"Received vote to start from {player_name}")


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

    def _register(self, player: Player):
        self._players[player.id] = player

    def _insert_input(self, keypress):
        self._my_keypress = keypress
        keyboard.remove_all_hotkeys()

    def _receiving_seats(self, action: Action):
        seat = action.get_data().get("seat")
        player = action.get_player()
        if seat:
            if self._round_inputs[seat] is None:
                self._round_inputs[seat] = player
                self._send_ack(player)
                return
        self._send_nak(player)
