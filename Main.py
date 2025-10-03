# main.py
from driver_api import DriverAPI

def main():
    # Force Fixed I/O (OUT) word at bytes 4..5 (little-endian)
    drv = DriverAPI("192.168.0.20", rpi_ms=10, fixed_out_offset=4)
    drv.connect()

    # Progress callback prints raw UDP + parsed app + decoded bits
    def progress(p):
        # RAW UDP (pre-CPF extraction): full datagram the listener received
        raw = drv.get_last_input_packet()
        print(f"RAW_UDP len={len(raw)} hex={raw.hex()}")

        # Parsed application payload (post-CTP/CPF extraction) used by the parser
        print(f"APP len={p['app_len']} hex={p['app_hex']}")

        # Decode Fixed I/O (OUT) word at offset 4..5 (little-endian)
        app = bytes.fromhex(p['app_hex'])
        w4 = int.from_bytes(app[4:6], 'little') if len(app) >= 6 else 0
        inpos = bool(w4 & 0x0004)           # IN-POS = bit 2 (0x0004)
        rem = f"{p['remaining_s']:.2f}s" if p['remaining_s'] is not None else "-"
        print(f"off={p['fixed_out_offset']} word@4=0x{w4:04X} INPOS(bit2)={inpos} rem={rem}")
        print("-" * 80)

    try:
        print("Starting Operation 2")
        ok2 = drv.Motor_Operation_2(timeout_s=30)
        print("op2:", ok2)

        drv.Pause(5, keep="stop")
        print("Starting Operation 1")

        ok1 = drv.Motor_Operation_1(timeout_s=30)
        print("op1:", ok1)
    finally:
        drv.close()

if __name__ == "__main__":
    main()
