# input_reader.py
"""Generic implicit input reader (driver→scanner Input data).

Assumes little-endian words. Fixed I/O (OUT) word is usually at bytes 4..5,
but some firmware places it at 8..9. We accept an explicit offset or
auto-detect on the first update().
"""
from dataclasses import dataclass
from typing import Optional

#These properties come from the Fixed IO output of the Driver
@dataclass
class FixedOutBits:
    raw: int
    @property
    def seq_bsy(self): return bool(self.raw & (1 << 0))
    @property
    def move(self):   return bool(self.raw & (1 << 1))
    @property
    def in_pos(self): return bool(self.raw & (1 << 2))  # 0x0004
    @property
    def start_r(self):return bool(self.raw & (1 << 3))
    @property
    def home_end(self):return bool(self.raw & (1 << 4))
    @property
    def ready(self):  return bool(self.raw & (1 << 5))
    @property
    def dcmd_rdy(self):return bool(self.raw & (1 << 6))
    @property
    def alm_a(self):  return bool(self.raw & (1 << 7))

#Class to handle reading of current drive state
class ImplicitInputReader:
    def __init__(self, fixed_out_offset: Optional[int] = None):
        self._last = b""
        self._fixed_out_offset: Optional[int] = fixed_out_offset  # 4 or 8

    #Updates the last message seen
    def update(self, app: bytes):
        self._last = app or b""
        if self._fixed_out_offset is None:
            self._fixed_out_offset = self._auto_pick_offset(self._last)
            
    #Used to grab fixed output of message based on first message sent
    def fixed_out(self) -> FixedOutBits:
        off = 4 if self._fixed_out_offset is None else self._fixed_out_offset
        if len(self._last) < off + 2:
            return FixedOutBits(0)
        return FixedOutBits(int.from_bytes(self._last[off:off+2], "little"))

    # convenience flags
    def in_pos(self) -> bool: return self.fixed_out().in_pos
    def move(self)   -> bool: return self.fixed_out().move
    def ready(self)  -> bool: return self.fixed_out().ready

    # === debugging helpers ===
    def last_app(self) -> bytes:
        """Return the last application bytes the parser has seen."""
        return self._last

    def fixed_out_offset_bytes(self) -> int:
        """Return the chosen Fixed I/O (OUT) offset (4 or 8)."""
        return self._fixed_out_offset or 4

    @staticmethod
    def _auto_pick_offset(b: bytes) -> int:
        # Prefer an offset that shows any of {IN-POS, MOVE, READY}
        candidates = [4, 8]
        mask = (1 << 2) | (1 << 1) | (1 << 5)
        for off in candidates:
            if len(b) >= off + 2:
                val = int.from_bytes(b[off:off+2], "little")
                if val & mask:
                    return off
        return 4

__all__ = ["FixedOutBits", "ImplicitInputReader"]
