# 
# NOTE: order should be like this : 
# Legacy Prefix | REX | Opcode | ModRM | SIB | Displacement | Immediate 
# 
# encoder takes IRProgram + SymbolTable and generates RAW bytes  
# 

import struct
from assembler.ir import (IRData, IRDirectives, IRInstructions, IRLabel, IRProgram, Instructions, Operand, OperandSize, OperandType, EncodingPref)
from assembler.symbol_table import SymbolTable
from assembler.error import EncoderError

# **** Register Encoding Table **** 

REG8 = {
    "AL": 0, "CL": 1, "DL": 2, "BL": 3,
    "AH": 4, "CH": 5, "DH": 6, "BH": 7,
    "SPL": 4, "BPL": 5, "SIL": 6, "DIL": 7,
    "R8B": 8, "R9B": 9, "R10B": 10, "R11B": 11,
    "R12B": 12, "R13B": 13, "R14B": 14, "R15B": 15,
}
REG16 = {
    "AX": 0, "CX": 1, "DX": 2, "BX": 3,
    "SP": 4, "BP": 5, "SI": 6, "DI": 7,
    "R8W": 8, "R9W": 9, "R10W": 10, "R11W": 11,
    "R12W": 12, "R13W": 13, "R14W": 14, "R15W": 15,
}
REG32 = {
    "EAX": 0, "ECX": 1, "EDX": 2, "EBX": 3,
    "ESP": 4, "EBP": 5, "ESI": 6, "EDI": 7,
    "R8D": 8, "R9D": 9, "R10D": 10, "R11D": 11,
    "R12D": 12, "R13D": 13, "R14D": 14, "R15D": 15,
}
REG64 = {
    "RAX": 0, "RCX": 1, "RDX": 2, "RBX": 3,
    "RSP": 4, "RBP": 5, "RSI": 6, "RDI": 7,
    "R8": 8,  "R9": 9,  "R10": 10, "R11": 11,
    "R12": 12, "R13": 13, "R14": 14, "R15": 15,
    "RIP": 5,  
}

ALLREGS = {}
ALLREGS.update(REG8)
ALLREGS.update(REG16)
ALLREGS.update(REG32)
ALLREGS.update(REG64)

def _reg_enc(name: str) -> int:
    """return register encoding (0-15), masking to 3 bits for ModRM"""
    n = name.upper()
    if n in ALLREGS:
        return ALLREGS[n] & 0x7   # low 3 bits for ModRM
    raise EncoderError(f"unknown register '{name}'")
 
 
def _reg_num(name: str) -> int:
    """return full register number (0-15) including extended"""
    n = name.upper()
    if n in ALLREGS:
        return ALLREGS[n]
    raise EncoderError(f"unknown register '{name}'")
 
 
def _is_64bit(name: str) -> bool:
    return name.upper() in REG64
 
 
def _is_32bit(name: str) -> bool:
    return name.upper() in REG32
 
 
def _is_16bit(name: str) -> bool:
    return name.upper() in REG16
 
 
def _is_8bit(name: str) -> bool:
    return name.upper() in REG8
 
 
def _is_extended(name: str) -> bool:
    """registers R8-R15 need REX.R or REX.B"""
    return _reg_num(name) >= 8


# **** Encoded Instructions  ***** 
"""
 each object holds as a byte , that means encoded as bytes and then it 
 assemble in corrected format : 
     Legacy Prefix | REX | Opcode | ModRM | SIB | Displacement | Immediate
"""
class EncodedInstructions:
    def __init__(self):
        self.legacy_prefix = b""
        self.rex = b""
        self.opcode = b""
        self.modrm  = b""
        self.sib = b""
        self.displacement = b""
        self.immediate = b""
    # combining to get total bytes 
    def to_bytes(self) -> bytes:
        total = (len(self.legacy_prefix) + len(self.rex) + len(self.opcode) + len(self.modrm) + len(self.sib) + len(self.displacement) + len(self.immediate))
        if total > 15: 
            raise EncoderError(
                f"instruction exceeds 15 byte limit: {total} bytes"
            )
        return self.legacy_prefix + self.rex + self.opcode + self.modrm + self.sib + self.displacement + self.immediate
    def __repr__(self):
        return f"Encoded({self.to_bytes().hex()})"
    
# **** Encoding each slot ****
# **** Encoding legacy prefix **** 

def encoding_legacy(
        operand_size_override: bool = False, 
        address_size: bool = False, 
        lock: bool = False, 
        rep: bool = False, 
        repne: bool = False,)-> bytes:
    prefix = b""
    if lock: prefix += b"\xF0"
    if repne: prefix += b"\xF2"
    if rep: prefix += b"\xF3"
    if operand_size_override: prefix += b"\x66"
    if address_size: prefix += b"\x67"
    return prefix

# *** encode REXbit ****
"""
RWXB : 1byte : 0100 : showing this is rex : 0000 : for RWXB 
W : 1000
R : 0100
X : 0010
B : 0001
"""
def encode_rex(w: bool, r: bool, x: bool, b: bool) -> bytes:
    if not([w, r, x, b]):
        return b""
    byte = 0x40 # 0100
    if w: byte |= 0x80
    if r: byte |= 0x04
    if x: byte |= 0x02
    if b: byte |= 0x01
    return bytes([byte])

def encode_modrm(mod: int, reg: int, rm: int) -> bytes: 
    """
    mod : 2 bits  00=mem 01=mem+disp8 10=mem+disp32 11=reg
    reg : 3 bits  register or opcode extension /0-/7
    rm  : 3 bits  register or memory base
    """
    assert 0 <= mod <= 3, f"mod out of range: {mod}"
    assert 0 <= reg <= 7, f"reg out of range: {reg}"
    assert 0 <= rm  <= 7, f"rm out of range: {rm}"
    return bytes([(mod << 6) | (reg << 3) | rm])

def encode_sib(scale: int, index: int, base: int) -> bytes:
    """
    scale: 1/2/4/8 -> encoded as 0/1/2/3
    index: 3 bits
    base:  3 bits
    """
    scale_enc = {1: 0, 2: 1, 4: 2, 8: 3}
    if scale not in scale_enc:
        raise EncoderError(f"invalid SIB scale: {scale}")
    return bytes([(scale_enc[scale] << 6) | (index << 3) | base])

def encode_displacement(value: int , size: int)-> bytes:
    """
    size: 0=none  1=8bit  4=32bit
    """
    if size == 0: return b""
    if size == 1: return struct.pack("<b", value)
    if size == 4: return struct.pack("<i", value)
    raise EncoderError(f"invalid displacement size: {size}")

def encode_immediate(value: int, size: int)-> bytes:
    """
    size: 1=imm8  2=imm16  4=imm32  8=imm64
    """
    fmts = {1: "<b", 2: "<h", 4: "<i", 8: "<q"}
    if size not in fmts:
        raise EncoderError(f"invalid immediate size: {size}")
    return struct.pack(fmts[size], value)

# **** Memory Operand Helper ****

# **** Instructions Encoder **** 
# **** Dispatch table **** 















