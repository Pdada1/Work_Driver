# input_listener.py
"""Small UDP listener for T→O implicit input (device → host).

Can share the same UDP socket as the transport (recommended),
or create its own legacy-bound socket if none is provided.
Parses CPF 0x00B1; falls back to [CTP seq (2B)] + app if CPF is absent.

Includes simple debugging helpers:
- get_last_packet(): raw last UDP packet bytes
- get_stats(): packet count, last length, last timestamp
"""
import socket, struct, threading, time
from typing import Optional

class UdpInputListener:
    def __init__(self, drive_ip: str, port: Optional[int] = None, bufsize: int = 4096,
                 udp_socket: Optional[socket.socket] = None):
        self.drive_ip = drive_ip
        self.port = port                 # only used if we create our own socket
        self.bufsize = bufsize
        self._ext_sock = udp_socket is not None
        self._sock: Optional[socket.socket] = udp_socket
        self._thr: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._latest = b""

        # debug state
        self._last_pkt = b""
        self._last_ts = 0.0
        self._count = 0

    def start(self) -> None:
        if self._thr and self._thr.is_alive():
            return
        self._stop.clear()
        if self._sock is None:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.settimeout(1.0)
            self._sock.bind(("", self.port or 2222))
        else:
            self._sock.settimeout(0.5)

        def _run():
            while not self._stop.is_set():
                try:
                    data, (_src_ip, _src_port) = self._sock.recvfrom(self.bufsize)

                    # record raw packet + simple stats (for debugging)
                    self._last_pkt = data
                    self._count += 1
                    self._last_ts = time.time()

                    # extract application bytes
                    app = self._extract_app_from_cpf(data)
                    if app is not None:
                        self._latest = app
                except socket.timeout:
                    continue
                except Exception:
                    continue

        self._thr = threading.Thread(target=_run, name="enip-udp-input", daemon=True)
        self._thr.start()

    def stop(self) -> None:
        self._stop.set()
        if not self._ext_sock:
            try:
                if self._sock:
                    self._sock.close()
            finally:
                self._sock = None

    def get_app(self) -> bytes:
        """Return last parsed application bytes (post-CTP/CPF extraction)."""
        return self._latest

    # === debugging helpers ===
    def get_last_packet(self) -> bytes:
        """Return the last raw UDP packet bytes (unparsed)."""
        return self._last_pkt

    def get_stats(self) -> dict:
        """Basic counters to verify we're receiving data."""
        return {
            "packets": self._count,
            "last_len": len(self._last_pkt),
            "last_ts": self._last_ts,
        }

    @staticmethod
    def _extract_app_from_cpf(pkt: bytes) -> Optional[bytes]:
        """Parse CPF and return 0x00B1 app (without 2B CTP). Fallback to pkt[2:]."""
        try:
            if len(pkt) >= 4:
                item_count = struct.unpack_from("<H", pkt, 0)[0]
                off = 2
                if 0 < item_count <= 8:
                    for _ in range(item_count):
                        if off + 4 > len(pkt): break
                        typ, ln = struct.unpack_from("<H H", pkt, off); off += 4
                        if off + ln > len(pkt): break
                        data = pkt[off:off+ln]; off += ln
                        if typ == 0x00B1 and ln >= 2:
                            return data[2:]
            if len(pkt) >= 2:
                return pkt[2:]
            return None
        except Exception:
            return None

__all__ = ["UdpInputListener"]
