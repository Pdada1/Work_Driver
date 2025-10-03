from driver_api import DriverAPI

drv = DriverAPI("192.168.0.20", rpi_ms=10)  
drv.connect()

ok2 = drv.Motor_Operation_2(timeout_s=30)
print(ok2)
drv.Pause(2, keep="stop")
print("Started op 1")
ok1 = drv.Motor_Operation_1(timeout_s=30)
print(ok1)
drv.close()
