# currently IR layer not nessary for the assembler (no we need this now)
# but will important for the shellengine 

# purpose : adding noise to instructions , register renaming and position 
            # independent code 

from isa.registers import Registers 
from isa.instructions import Instructions 

class OperandType: 
    REGISTER = "REGISTER"
    IMMEDIATE = "IMMEDIATE"
    MEMORY = "MEMORY"
    LABEL_REF = "LABEL_REF"

class OperandSize: 
    NONE = 0
    BYTE = 8
    WORD = 16 
    DWORD = 32 
    QWORD = 64

class EncodingPref:                          # ← fixed: was ENCODINGS
    DEFAULT = "DEFAULT"
    SHORTEST = "SHORTESTS"
    AVOID_NULL = "AVOID_NULL"
    FORCE_REX = "FORCE_REX" # emit rex if it not needed 
    FORCE_VEX = "FORCE_VEX" # this replace old SSE bytes


# **** ISA Table ****
_R = Registers()
_INS = Instructions()

REGISTER_SIZE = {}
# here we store size of each operand inside the REGISTER_SIZE array 
for r in _R.R_8:      REGISTER_SIZE[r] = OperandSize.BYTE
for r in _R.ELB:      REGISTER_SIZE[r] = OperandSize.BYTE
for r in _R.R_16:     REGISTER_SIZE[r] = OperandSize.WORD
for r in _R.SEGMENT:  REGISTER_SIZE[r] = OperandSize.WORD
for r in _R.IP_16:    REGISTER_SIZE[r] = OperandSize.WORD
for r in _R.R_32:     REGISTER_SIZE[r] = OperandSize.DWORD
for r in _R.IP_32:    REGISTER_SIZE[r] = OperandSize.DWORD
for r in _R.FPC:      REGISTER_SIZE[r] = OperandSize.DWORD
for r in _R.R_64:     REGISTER_SIZE[r] = OperandSize.QWORD
for r in _R.IP_64:    REGISTER_SIZE[r] = OperandSize.QWORD
for r in _R.CONTROL:  REGISTER_SIZE[r] = OperandSize.QWORD
for r in _R.DEBUG:    REGISTER_SIZE[r] = OperandSize.QWORD
for r in _R.SIMD:     REGISTER_SIZE[r] = OperandSize.QWORD
for r in _R.AVX:      REGISTER_SIZE[r] = OperandSize.QWORD
for r in _R.FLAGS:    REGISTER_SIZE[r] = OperandSize.NONE
for r in _R.RFLAGS:   REGISTER_SIZE[r] = OperandSize.NONE

# MNEMONIC -> Opcode Lookup 
# "MOV" -> [b"\x89", b"\x8B", ...]
OPCODE_TABLE = {}
for name, opcodes in _INS.GPA_OPS.items():    OPCODE_TABLE[name] = opcodes
for name, opcodes in _INS.DATA_T.items():     OPCODE_TABLE[name] = opcodes
for name, opcodes in _INS.CFI.items():        OPCODE_TABLE[name] = opcodes
for name, opcodes in _INS.BIT_MANI.items():   OPCODE_TABLE[name] = opcodes
for name, opcodes in _INS.SSE.items():        OPCODE_TABLE[name] = opcodes
for name, opcodes in _INS.SYSTEM_INS.items(): OPCODE_TABLE[name] = opcodes

# *** Operands  **** 
class Operand: 
    def __init__(self, op_type, value , size=OperandSize.NONE):
        self.op_type = op_type # Operand type 
        self.value = value # main or EAX or numbers like 55 
        self.size = size # operand size 
        # mem field : [BASE + INDEX * SCALE + DISP]
        self.base = None # base register 
        self.index = None # index register 
        self.scale = 1 # 1 , 2 ,4 ,8 , 16 , 32 , 64  
        self.disp = 0 # displacement 

        # shellcode 
        self.is_rip_relative = False # when the operand using RIP relative addressing

    def __repr__(self):
        return f"Operand({self.op_type}, {self.value}, size={self.size})"  # ← fixed: was self.kind

# **** IR Nodes  ****
class IRInstructions: 
    def __init__(self, mnemonic, operands=None , line=0, column=0):  # ← fixed: NONE → None
        self.mnemonic = mnemonic
        self.operands = operands if operands is not None else []
        self.line = line
        self.column = column 
        # Opcodes from instructions.py 
        # encoder picks the right one based on operands 
        self.opcode = OPCODE_TABLE.get(mnemonic, [])
        # PIC test (purpose:mainly for shellcode engine )
        self.pic_good = False # good for PIC analysis 
        self.uses_abs = False # using Absolute address
        # Encoding 
        self.enc_pref  = EncodingPref.DEFAULT  # ← fixed: class renamed
        self.enc_bytes = None # filled by encoder 

        self.forbidden = set()
        self.satisfies_constraints = True

    def __repr__(self):
        ops = ", ".join(repr(o) for o in self.operands)
        return f"IRInstruction({self.mnemonic}, [{ops}])"

class IRLabel: # this is for labels like "main: "
    def __init__(self, name, line=0, column=0):
        self.name = name
        self.line = line 
        self.column = column
        self.is_local = name.startswith(".")
        self.offset = None
    def __repr__(self):
        return f"IRLabel({self.name!r}, local={self.is_local})"

class IRDirectives: 
    def __init__(self, name , args=None, line=0, column=0):
        self.name = name
        self.args = args if args is not None else []
        self.line = line 
        self.column = column
    def __repr__(self):
        return f"IRDirective({self.name!r}, {self.args})"

class IRData: 
    def __init__(self, label, size, values=None, line=0):
        self.label = label 
        self.size = size
        self.values = values if values is not None else []
        self.line = line
    def __repr__(self):
        return f"IRData({self.label!r}, size={self.size}, {self.values})"


# **** FOR SHELLCODE ****
class ShellcodeConstraints:
    """
    set via directives in source:
        BADCHARS  0x00 0x0a 0x0d
        MAX_SIZE  64
        PIC_MODE  ON
        ENCODING  AVOID_NULL
    """
    def __init__(self):
        self.forbidden_bytes = set()
        self.max_size = 0 # 0 = unlimited
        self.pic_mode = False
        self.encoding_pref = EncodingPref.DEFAULT  # ← fixed: class renamed

    def add_badchar(self, byte):
        self.forbidden_bytes.add(byte)

    def is_byte_ok(self, byte):
        return byte not in self.forbidden_bytes

    def check_bytes(self, raw_bytes):
        # returns list of (offset, byte) violations
        violations = []
        for i, b in enumerate(raw_bytes):
            if b in self.forbidden_bytes:
                violations.append((i, b))
        return violations

    def __repr__(self):
        return (
            f"ShellcodeConstraints("
            f"badchars={[hex(b) for b in self.forbidden_bytes]}, "
            f"max_size={self.max_size}, "
            f"pic={self.pic_mode}, "
            f"enc={self.encoding_pref})"
        )
 
# **** IR Layer **** 
class IRProgram: 
    def __init__(self):
        self.nodes       = []
        self.constraints = ShellcodeConstraints()
        self.symbols     = {}   # label name -> byte offset, filled by encoder

    def add(self, node):
        self.nodes.append(node)

    def instructions(self):
        return [n for n in self.nodes if isinstance(n, IRInstructions)] 

    def labels(self):
        return [n for n in self.nodes if isinstance(n, IRLabel)]

    def directives(self):
        return [n for n in self.nodes if isinstance(n, IRDirectives)] 

    def data(self):
        return [n for n in self.nodes if isinstance(n, IRData)]

    def dump(self):
        print("=" * 60)
        print(f"  constraints : {self.constraints}")
        print(f"  symbols     : {self.symbols}")
        print("=" * 60)
        for node in self.nodes:

            if isinstance(node, IRInstructions):                         
                ops = ", ".join(
                    f"{o.op_type}:{o.value!r}(sz={o.size})"          
                    for o in node.operands
                )
                print(
                    f"  INSTR   {node.mnemonic:<14}"
                    f"  ops=[{ops}]"
                    f"  pic={node.pic_good}"                              
                    f"  enc={node.enc_pref}"
                )

            elif isinstance(node, IRLabel):
                print(
                    f"  LABEL   {node.name:<14}"
                    f"  local={node.is_local}"
                    f"  offset={node.offset}"
                )

            elif isinstance(node, IRDirectives):                         
                print(
                    f"  DIR     {node.name:<14}"
                    f"  args={node.args}"
                )

            elif isinstance(node, IRData):
                print(
                    f"  DATA    {str(node.label):<14}"
                    f"  size={node.size}"
                    f"  values={node.values}"
                )

        print("=" * 60)