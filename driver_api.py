# driver_api.py
"""High-level operations; composes transport + input reader/listener."""
import time
from typing import Optional, Callable, Union
from interfaces import Transport  # kept for compatibility if you later inject a mock
from enip_transport import EnipSender
from input_reader import ImplicitInputReader
from input_listener import UdpInputListener
from types_hex import MOTOR_JOG, MOTOR_STOP, MOTOR_OP_1, MOTOR_OP_2

ProgressFn = Callable[[dict], None]

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
    def Motor_Jog(self, duration_s: float = 1.0, progress: Optional[ProgressFn] = None):
        self.tx.update_app(MOTOR_JOG)
        end = time.time() + max(0.0, duration_s)
        while time.time() < end:
            time.sleep(self.rpi_ms / 1000.0)
            self._poll_input_once()
            if progress:
                self._emit_progress(progress, started=True)
        self.Motor_Stop(progress=progress)

    def Motor_Stop(self, progress: Optional[ProgressFn] = None):
        self.tx.update_app(MOTOR_STOP)
        # give it a couple of cycles
        for _ in range(3):
            time.sleep(self.rpi_ms / 1000.0)
            self._poll_input_once()
            if progress:
                self._emit_progress(progress)

    def Motor_Operation_1(self, timeout_s: float = 10.0, progress: Optional[ProgressFn] = None) -> bool:
        return self._op_until_inpos(MOTOR_OP_1, timeout_s, progress=progress)

    def Motor_Operation_2(self, timeout_s: float = 10.0, progress: Optional[ProgressFn] = None) -> bool:
        return self._op_until_inpos(MOTOR_OP_2, timeout_s, progress=progress)

    # Hold START in the stream until IN-POS is seen, then STOP once
    def _op_until_inpos(self, payload: bytes, timeout_s: float, progress: Optional[ProgressFn]) -> bool:
        self.tx.update_app(payload)
        t0 = time.time()
        deadline = t0 + max(0.0, timeout_s)
        while time.time() < deadline:
            time.sleep(self.rpi_ms / 1000.0)
            self._poll_input_once()
            if progress:
                self._emit_progress(progress, started=True, t0=t0, deadline=deadline)
            if self.input.in_pos():
                self.Motor_Stop(progress=progress)
                return True
        # timeout safety
        self.Motor_Stop(progress=progress)
        return False

    def Pause(self, seconds: float, keep: Union[str, bytes] = "stop", progress: Optional[ProgressFn] = None):
        """
        Delay between operations without disrupting the cyclic sender.
        - keep="stop": assert MOTOR_STOP during the pause (default)
        - keep="hold": keep whatever app is currently being streamed
        - keep=<bytes>: stream a custom 44B app payload during the pause
        """
        seconds = max(0.0, float(seconds))

        if isinstance(keep, (bytes, bytearray)):
            self.tx.update_app(bytes(keep))
        elif isinstance(keep, str):
            k = keep.lower()
            if k == "stop":
                self.tx.update_app(MOTOR_STOP)
            elif k == "hold":
                pass
            else:
                raise ValueError("keep must be 'stop', 'hold', or bytes payload")
        else:
            raise TypeError("keep must be str or bytes")

        end = time.monotonic() + seconds
        step = max(self.rpi_ms / 1000.0, 0.005)
        while time.monotonic() < end:
            self._poll_input_once()
            if progress:
                self._emit_progress(progress)
            time.sleep(step)

    # ===== debugging helpers (peek what the listener/parser sees) =====
    def get_last_input_app(self) -> bytes:
        """Return the most recent parsed application bytes (what the parser uses)."""
        if self._listener:
            return self._listener.get_app()
        return self._get_in() or b""

    def get_last_input_packet(self) -> bytes:
        """Return the most recent raw UDP packet (before CPF/app extraction)."""
        if self._listener and hasattr(self._listener, "get_last_packet"):
            return self._listener.get_last_packet()
        return b""

    def debug_input_snapshot(self) -> str:
        """Human-friendly one-liner showing app length, hex, Fixed I/O word and bits."""
        app = self.get_last_input_app()
        off = getattr(self.input, "_fixed_out_offset", None) or 4
        word = int.from_bytes(app[off:off+2], "little") if len(app) >= off + 2 else 0
        bits = "".join("1" if word & (1 << i) else "0" for i in range(15, -1, -1))
        return (
            f"app_len={len(app)} off={off} fixed_out=0x{word:04X} "
            f"bits(MSB→LSB)={bits} app_hex={app.hex()}"
        )

    # emit a dict to any progress callback
    def _emit_progress(self, cb: ProgressFn, started: bool = False,
                       t0: Optional[float] = None, deadline: Optional[float] = None):
        app = self.get_last_input_app()
        off = getattr(self.input, "_fixed_out_offset", None) or 4
        raw = int.from_bytes(app[off:off+2], "little") if len(app) >= off + 2 else 0
        flags = self.input.fixed_out()
        now = time.time()
        payload = {
            "ts": now,
            "elapsed_s": (now - t0) if t0 else None,
            "remaining_s": (deadline - now) if deadline else None,
            "fixed_out_offset": off,
            "fixed_out_raw": raw,
            "in_pos": flags.in_pos,
            "move": flags.move,
            "ready": flags.ready,
            "app_len": len(app),
            "app_hex": app.hex(),
            "started": started,
        }
        try:
            cb(payload)
        except Exception:
            pass

__all__ = ["DriverAPI"]
