# enip_transport.py
"""EtherNet/IP encapsulation + UDP/2222 sender (transport)."""
from __future__ import annotations
import socket, struct, threading, time
from typing import Optional
from hexutil import hx
from types_hex import REGISTER_SESSION_HEX, FORWARD_OPEN_HEX

class EnipSender:
    def __init__(self, drive_ip: str, tcp_port: int = 44818, udp_port: int = 2222):
        self.drive_ip = drive_ip
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self._tcp: Optional[socket.socket] = None

        # Create ONE UDP socket for both send and recv, and BIND IT to 2222.
        self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass
        self._udp.bind(("", self.udp_port))   # <<< THIS IS THE IMPORTANT LINE
        self._udp.settimeout(1.0)

        self.session = 0
        self.conn_id = 0
        self.seq_ctp = 1
        self.seq_sai = 1

        # cyclic sender state to continiously send message so connection stays open
        self._cyc_thread: Optional[threading.Thread] = None
        self._cyc_stop = threading.Event()
        self._rpi_s = 0.010
        self._mirror = False
        self._o2t_size = 44
        self._current_app = b"\x00" * 44
        self._lock = threading.Lock()

    #Function to register initial session 
    def connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((self.drive_ip, self.tcp_port))
        s.sendall(hx(REGISTER_SESSION_HEX))
        reg = s.recv(8192)
        self.session = int.from_bytes(reg[4:8], "little") if len(reg) >= 8 else 0
        if self.session == 0:
            s.close(); raise RuntimeError("RegisterSession failed")
        fo = bytearray(hx(FORWARD_OPEN_HEX)); fo[4:8] = self.session.to_bytes(4, "little")
        s.sendall(bytes(fo))
        rep = s.recv(8192)
        self.conn_id = self._parse_forward_open_o2t(rep) or 0
        if self.conn_id == 0:
            s.close(); raise RuntimeError("ForwardOpen failed")
        # Pin UDP to adapter peer so inbound T→O lands on this socket/port
        try:
            self._udp.connect((self.drive_ip, self.udp_port))
        except Exception:
            pass
        self._tcp = s

    #Used to close connection
    def close(self):
        self.stop_cyclic()
        try:
            if self._tcp:
                self._tcp.close()
        finally:
            self._tcp = None
            self.session = 0
            self.conn_id = 0

    # One-shot send to send a packet once if required
    def send_app(self, app: bytes, mirror_over_tcp: bool = False):
        if not (self._tcp and self.conn_id):
            raise RuntimeError("Not connected")
        cpf = self._build_udp_io_cpf(self.conn_id, self.seq_ctp, self.seq_sai, app)
        self._udp.sendto(cpf, (self.drive_ip, self.udp_port))
        if mirror_over_tcp:
            self._send_unit_data_over_tcp(self._tcp, self.session, cpf)
        self.seq_ctp = (self.seq_ctp + 1) & 0xFFFF
        self.seq_sai = (self.seq_sai + 1) & 0xFFFF

    # === Cyclic background stream to keep Class-1 alive ===
    def start_cyclic(self, rpi_ms: int = 10, mirror_over_tcp: bool = False, o2t_size: int = 44):
        self._rpi_s = max(0.001, rpi_ms / 1000.0)
        self._mirror = bool(mirror_over_tcp)
        self._o2t_size = max(0, int(o2t_size))
        if self._cyc_thread and self._cyc_thread.is_alive():
            return
        self._cyc_stop.clear()

        def _run():
            while not self._cyc_stop.is_set():
                try:
                    with self._lock:
                        app = (self._current_app + b"\x00"*self._o2t_size)[:self._o2t_size]
                    self.send_app(app, mirror_over_tcp=self._mirror)
                except Exception:
                    # Attempt to recover TCP + ForwardOpen (device may have closed us)
                    try:
                        if self._tcp:
                            self._tcp.close()
                    except Exception:
                        pass
                    self._tcp = None
                    backoff = 0.2
                    while not self._cyc_stop.is_set():
                        try:
                            self.connect()
                            break
                        except Exception:
                            time.sleep(backoff)
                            backoff = min(2.0, backoff * 2)
                time.sleep(self._rpi_s)

        self._cyc_thread = threading.Thread(target=_run, name="enip-cyclic", daemon=True)
        self._cyc_thread.start()

    #Used to gracefully halt the cyclic sending in order to close a conenction
    def stop_cyclic(self, join_timeout: float = 2.0):
        if self._cyc_thread and self._cyc_thread.is_alive():
            self._cyc_stop.set()
            self._cyc_thread.join(timeout=join_timeout)
        self._cyc_thread = None
        self._cyc_stop.clear()

    #Update what the message being sent to driver is with new payload
    def update_app(self, app: bytes):
        """Update the current O→T payload the cyclic sender transmits."""
        with self._lock:
            self._current_app = app or b""
            
    #Returns current UDP socket for input listener
    def udp_socket(self) -> socket.socket:
        """Expose shared UDP socket (for input listener)."""
        return self._udp

    # --- helpers ---
    @staticmethod
    def _build_udp_io_cpf(conn_id: int, seq_ctp: int, seq_sai: int, app: bytes) -> bytes:
        sai = struct.pack("<I H H", conn_id, seq_sai & 0xFFFF, 0)
        ctp = struct.pack("<H", seq_ctp & 0xFFFF) + app
        return (struct.pack("<H", 2) +
                struct.pack("<H H", 0x8002, len(sai)) + sai +
                struct.pack("<H H", 0x00B1, len(ctp)) + ctp)

    @staticmethod
    def _send_unit_data_over_tcp(sock: socket.socket, session: int, cpf: bytes) -> None:
        payload = struct.pack("<I H H", 0, 0, 2) + cpf
        encap   = struct.pack("<HHI I 8s I", 0x0070, len(payload), session, 0, b"\x00"*8, 0) + payload
        sock.sendall(encap)

    @staticmethod
    def _parse_forward_open_o2t(encap_reply: bytes) -> Optional[int]:
        if len(encap_reply) < 24: return None
        _, ln, _, status = struct.unpack_from("<H H I I", encap_reply, 0)
        if status != 0 or len(encap_reply) < 24 + ln: return None
        rr = encap_reply[24:24+ln]
        if len(rr) < 8: return None
        item_count = struct.unpack_from("<H", rr, 6)[0]
        off = 8; cip = None
        for _ in range(item_count):
            if off + 4 > len(rr): return None
            typ, l = struct.unpack_from("<H H", rr, off); off += 4
            if off + l > len(rr): return None
            data = rr[off:off+l]; off += l
            if typ in (0x00B2, 0x00B0): cip = data
        if not cip or len(cip) < 2: return None
        path_words = cip[1]; pos = 2 + 2*path_words
        if pos + 2 > len(cip): return None
        gen = cip[pos]; ext = cip[pos+1]; pos += 2 + 2*ext
        if gen != 0x00 or pos + 4 > len(cip): return None
        return struct.unpack_from("<I", cip, pos)[0]

__all__ = ["EnipSender"]
