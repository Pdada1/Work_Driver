# hexutil.py
import binascii

def hx(s: str) -> bytes:
    """Lenient hex-to-bytes (strips non-hex, left-pads odd length)."""
    s = "".join(c for c in s if c in "0123456789abcdefABCDEF")
    if len(s) % 2:
        s = "0" + s
    return binascii.unhexlify(s)

__all__ = ["hx"]