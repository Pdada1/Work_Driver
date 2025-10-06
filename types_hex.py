# types_hex.py
from hexutil import hx

# Proven encapsulation frames
REGISTER_SESSION_HEX = "65000400000000000000000000000000000000000000000001000000"
FORWARD_OPEN_HEX = (
    "6f004a000100000000000000000000000100008000000000000000000000020000000000b2003a00"
    "540220062401059c0000000001400100020001003814947002000000102700002e48102700003a48"
    "01083404bb002b00e613810120042c652c64"
)

# Explicit 44B O→T application payloads (field-by-field)
MOTOR_JOG = hx(
    "01000000"  # R-IN (DWORD)
    "0000"      # Mx select (UINT16)
    "0000"      # padding
    "0100"      # Fixed I/O (IN): bit0 = FW-JOG
    "0000"      # padding
    "00000000" "00000000" "00000000" "00000000"  # 4x DWORD op data
    "0000" "0000" "0000" "0000"                   # padding
    "0000" "0000" "0000" "0000"
)

MOTOR_STOP = hx(
    "01000000"
    "0000"
    "0000"
    "2000"      # bit5 = STOP
    "0000"
    "00000000" "00000000" "00000000" "00000000"
    "0000" "0000" "0000" "0000"
    "0000" "0000" "0000" "0000"
)

MOTOR_OP_1 = hx(
    "01000000"
    "0000"
    "0000"
    "0800"      # bit3 = START
    "0000"
    "00000000" "00000000" "00000000" "00000000"
    "0000" "0000" "0000" "0000"
    "0000" "0000" "0000" "0000"
)


MOTOR_OP_2 = hx(
    "01000000"
    "0000"      # M0 select
    "0100"
    "0800"      # START
    "0000"
    "00000000" "00000000" "00000000" "00000000"
    "0000" "0000" "0000" "0000"
    "0000" "0000" "0000" "0000"
)

motor_angle = (
    "01000000"  #Intial header for UDP packets, dont change
    "0000"      #Remote IO accessed
    "0000"      #Operation Number Selection (M0-M7)
    "0001"      # Fixed IO
    "0100"      # DD operation type
    "00000000"  # The step setting for position target goes from -2^31 to 2^31-1
    "E8030000"  # The speed setting for operation
    "40420f00"  # Starting Acceleration
    "40420f00"  # Decelleration
    "E803"      # Operating Current
    "0000"      # Forwarding Destination (keep 0)
    "0000"      #All others are 0
    "0000"      
    "0000" "0000" "0000" "0000" 
)

MOTOR_TRIGGER = hx(
    "01000000"  #Intial header for UDP packets, dont change
    "0000"     
    "0000"      
    "0001"      # Fixed IO, bit 8 set for trigger
    "0000"      
    "00000000"  
    "00000000" 
    "00000000"  
    "00000000"  
    "0000"      
    "0000"      
    "0000"     
    "0000"      
    "0000" "0000" "0000" "0000" 
)

MOTOR_DETRIGGER = hx(
    "01000000"  #Intial header for UDP packets, dont change
    "0000"     
    "0000"      
    "0000"      # Fixed IO, bit 8 unset for detrigger
    "0000"      
    "00000000"  
    "00000000" 
    "00000000"  
    "00000000"  
    "0000"      
    "0000"      
    "0000"     
    "0000"      
    "0000" "0000" "0000" "0000" 
)

MOTOR_FREE = hx(
    "01000000"
    "0000"
    "0000"
    "4000"      # bit6 = FREE
    "0000"
    "00000000" "00000000" "00000000" "00000000"
    "0000" "0000" "0000" "0000"
    "0000" "0000" "0000" "0000"
)

MOTOR_NO_OP = hx(
    "01000000"
    "0000"
    "0010"
    "0008"      # bit11 = Reserved, used as NO-OP
    "0000"
    "00000000" "00000000" "00000000" "00000000"
    "0000" "0000" "0000" "0000"
    "0000" "0000" "0000" "0000"
)

# Guard against accidental edits
for _name, _val in {
    "MOTOR_JOG": MOTOR_JOG,
    "MOTOR_STOP": MOTOR_STOP,
    "MOTOR_OP_1": MOTOR_OP_1,
    "MOTOR_OP_2": MOTOR_OP_2,
    "MOTOR_FREE": MOTOR_FREE,
}.items():
    assert len(_val) == 44, f"{_name} must be 44 bytes, got {len(_val)}"

__all__ = [
    "REGISTER_SESSION_HEX", "FORWARD_OPEN_HEX",
    "MOTOR_JOG", "MOTOR_STOP", "MOTOR_OP_1", "MOTOR_OP_2", "MOTOR_FREE",
]
