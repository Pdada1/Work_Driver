from driver_api import DriverAPI

def progress(p):
    # Example: print a one-liner with IN-POS and the fixed-out word (little-endian)
    rem = f"{p['remaining_s']:.2f}s" if p['remaining_s'] is not None else "-"
    print(f"IN-POS={p['in_pos']}  word=0x{p['fixed_out_raw']:04X}  rem={rem}")

drv = DriverAPI("192.168.0.20", rpi_ms=10)
drv.connect()

ok2 = drv.Motor_Operation_2(timeout_s=30, progress=progress)
print(ok2)

drv.Pause(2, keep="stop", progress=progress)
print("Started op 1")

ok1 = drv.Motor_Operation_1(timeout_s=30, progress=progress)
print(ok1)

drv.close()
