# types_hex.py
from hexutil import hx

# Register session hex from Allen-Bradley PLC
REGISTER_SESSION_HEX = "65000400000000000000000000000000000000000000000001000000"
#Forward session hex from Allen-Bradley PLC
FORWARD_OPEN_HEX = (
    "6f004a000100000000000000000000000100008000000000000000000000020000000000b2003a00"
    "540220062401059c0000000001400100020001003814947002000000102700002e48102700003a48"
    "01083404bb002b00e613810120042c652c64"
)

#Motor Jog bytecode
MOTOR_JOG = hx(
    "01000000"  
    "0000"      
    "0000"      
    "0100"      # Fixed I/O (IN): bit0 = FW-JOG
    "0000"      
    "00000000" "00000000" "00000000" "00000000"  
    "0000" "0000" "0000" "0000"                   
    "0000" "0000" "0000" "0000"
)

#Motor Stop bytecode
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
#Motor Operation 1 selection
MOTOR_OP_1 = hx(
    "01000000"
    "0000"      
    "0000"      #M0-M7 for op sel, OP 1 corresponds to 0
    "0800"      # bit3 = START
    "0000"
    "00000000" "00000000" "00000000" "00000000"
    "0000" "0000" "0000" "0000"
    "0000" "0000" "0000" "0000"
)

#Motor Operation 2 selection
MOTOR_OP_2 = hx(
    "01000000"
    "0000"      
    "0100"      #M0-M7 for op sel, OP 2 corresponds to 1
    "0800"      # bit3 = START
    "0000"
    "00000000" "00000000" "00000000" "00000000"
    "0000" "0000" "0000" "0000"
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
