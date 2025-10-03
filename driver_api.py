# driver_api.py
"""High-level operations; composes transport + input reader/listener."""
import time
from typing import Optional, Callable
from interfaces import Transport  # kept for compatibility if you later inject a mock
from enip_transport import EnipSender
from input_reader import ImplicitInputReader
from input_listener import UdpInputListener
from types_hex import MOTOR_JOG, MOTOR_STOP, MOTOR_OP_1, MOTOR_OP_2

class DriverAPI:
    def __init__(self, drive_ip: str, rpi_ms: int = 10,
                 get_input_app: Optional[Callable[[], bytes]] = None,
                 mirror_over_tcp: bool = False,
                 listen_port: int = 2222,             # used only if not sharing socket
                 transport: Optional[Transport] = None,
                 fixed_out_offset: Optional[int] = None):
        # rely on EnipSender so we can call start_cyclic/update_app
        self.tx: EnipSender = transport or EnipSender(drive_ip)
        self.input = ImplicitInputReader(fixed_out_offset=fixed_out_offset)
        self.rpi_ms = max(1, int(rpi_ms))
        self.mirror = bool(mirror_over_tcp)

        self._listener: Optional[UdpInputListener] = None
        self._listener_pending = False

        if get_input_app is not None:
            self._get_in = get_input_app
        else:
            # Share SAME UDP socket as transport; start after connect()
            shared_sock = self.tx.udp_socket()
            self._listener = UdpInputListener(drive_ip, port=listen_port, udp_socket=shared_sock)
            self._get_in = self._listener.get_app
            self._listener_pending = True

    # lifecycle
    def connect(self):
        self.tx.connect()
        if self._listener and self._listener_pending:
            self._listener.start()
            self._listener_pending = False
        # keep the Class-1 connection alive continuously
        self.tx.update_app(MOTOR_STOP)  # idle baseline
        self.tx.start_cyclic(rpi_ms=self.rpi_ms, mirror_over_tcp=self.mirror, o2t_size=44)

    def close(self):
        self.tx.stop_cyclic()
        self.tx.close()
        if self._listener:
            self._listener.stop()

    # ---- internal: poll input once (from listener/shared socket) ----
    def _poll_input_once(self):
        try:
            data = self._get_in() or b""
            if data:
                self.input.update(data)
        except Exception:
            pass

    # ---- public helpers (set desired app; cyclic sender transmits it) ----
    def Motor_Jog(self, duration_s: float = 1.0):
        self.tx.update_app(MOTOR_JOG)
        end = time.time() + max(0.0, duration_s)
        while time.time() < end:
            time.sleep(self.rpi_ms / 1000.0)
            self._poll_input_once()
        self.Motor_Stop()

    def Motor_Stop(self):
        self.tx.update_app(MOTOR_STOP)
        # give it a couple of cycles
        for _ in range(3):
            time.sleep(self.rpi_ms / 1000.0)
            self._poll_input_once()

    def Motor_Operation_1(self, timeout_s: float = 10.0) -> bool:
        return self._op_until_inpos(MOTOR_OP_1, timeout_s)

    def Motor_Operation_2(self, timeout_s: float = 10.0) -> bool:
        return self._op_until_inpos(MOTOR_OP_2, timeout_s)

    def _op_until_inpos(self, payload: bytes, timeout_s: float) -> bool:
        # Hold START in the stream until IN-POS is seen, then STOP once
        self.tx.update_app(payload)
        deadline = time.time() + max(0.0, timeout_s)
        while time.time() < deadline:
            time.sleep(self.rpi_ms / 1000.0)
            self._poll_input_once()
            if self.input.in_pos():
                self.Motor_Stop()
                return True
        # timeout safety
        self.Motor_Stop()
        return False

    def Pause(self, seconds: float, keep: str | bytes = "stop"):
        """
        Delay between operations without disrupting the cyclic sender.
        - keep="stop": assert MOTOR_STOP during the pause (default)
        - keep="hold": keep whatever app is currently being streamed
        - keep=<bytes>: stream a custom 44B app payload during the pause
        """
        seconds = max(0.0, float(seconds))

        if isinstance(keep, bytes):
            self.tx.update_app(keep)
        elif isinstance(keep, str):
            if keep.lower() == "stop":
                self.tx.update_app(MOTOR_STOP)
            elif keep.lower() == "hold":
                pass  # leave current app as-is
            else:
                raise ValueError("keep must be 'stop', 'hold', or bytes payload")
        else:
            raise TypeError("keep must be str or bytes")

        # Loop in small steps so we keep ingesting T→O input frames for status
        end = time.monotonic() + seconds
        step = max(self.rpi_ms / 1000.0, 0.005)
        while time.monotonic() < end:
            self._poll_input_once()       # keep status fresh during the pause
            time.sleep(step)


__all__ = ["DriverAPI"]
