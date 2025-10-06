# main.py
from driver_api import DriverAPI
from typing import Final

IP_ADDRESS: Final="192.168.0.20"
RPI_MS: Final=10
FIXED_OFFSET: Final=4
MOVE_TIMEOUT: Final=20


def main():
    # Force Fixed I/O (OUT) word at bytes 4..5 (little-endian)
    drv = DriverAPI(IP_ADDRESS, rpi_ms=RPI_MS, fixed_out_offset=FIXED_OFFSET)
    drv.connect()
    try:
        #print("Starting Operation 2")
        #ok2 = drv.Motor_Operation_2(timeout_s=MOVE_TIMEOUT)
        #print("op2:", ok2)

        #drv.Pause(5, keep="stop")
        #print("Starting Operation 1")

        #ok1 = drv.Motor_Operation_2(timeout_s=MOVE_TIMEOUT)
        #print("op1:", ok1)
        drv.Motor_Trig()
    finally:
        drv.close()

if __name__ == "__main__":
    main()
