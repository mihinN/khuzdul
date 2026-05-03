# assembler/encoder.py
#
# NOTE: order should be like this :
# Legacy Prefix | REX | Opcode | ModRM | SIB | Displacement | Immediate
#
# encoder takes IRProgram + SymbolTable and generates RAW bytes
#

import struct
from assembler.ir import (
    IRData, IRDirectives, IRInstructions, IRLabel, IRProgram,
    Operand, OperandSize, OperandType, EncodingPref,
)
from assembler.symbol_table import SymbolTable
from assembler.error import EncoderError


# **** Register Encoding Tables ****

REG8 = {
    "AL": 0,  "CL": 1,  "DL": 2,   "BL": 3,
    "AH": 4,  "CH": 5,  "DH": 6,   "BH": 7,
    # extended 8-bit (require REX prefix)
    "SPL": 4, "BPL": 5, "SIL": 6,  "DIL": 7,
    "R8B": 8, "R9B": 9, "R10B": 10,"R11B": 11,
    "R12B":12,"R13B":13,"R14B": 14,"R15B": 15,
}

REG16 = {
    "AX": 0,  "CX": 1,  "DX": 2,   "BX": 3,
    "SP": 4,  "BP": 5,  "SI": 6,   "DI": 7,
    "R8W": 8, "R9W": 9, "R10W":10, "R11W":11,
    "R12W":12,"R13W":13,"R14W": 14,"R15W":15,
}

REG32 = {
    "EAX": 0, "ECX": 1, "EDX": 2,  "EBX": 3,
    "ESP": 4, "EBP": 5, "ESI": 6,  "EDI": 7,
    "R8D": 8, "R9D": 9, "R10D":10, "R11D":11,
    "R12D":12,"R13D":13,"R14D": 14,"R15D":15,
}

REG64 = {
    "RAX": 0, "RCX": 1, "RDX": 2,  "RBX": 3,
    "RSP": 4, "RBP": 5, "RSI": 6,  "RDI": 7,
    "R8":  8, "R9":  9, "R10": 10, "R11": 11,
    "R12":12, "R13":13, "R14": 14, "R15": 15,
    "RIP": 5,   # RIP encoded as RBP in ModRM with mod=00
}

ALLREGS = {}
ALLREGS.update(REG8)
ALLREGS.update(REG16)
ALLREGS.update(REG32)
ALLREGS.update(REG64)


def _reg_enc(name: str) -> int:
    """return register encoding masked to 3 bits for ModRM"""
    n = name.upper()
    if n in ALLREGS:
        return ALLREGS[n] & 0x7
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


# **** Encoded Instruction Container ****
"""
each field holds bytes for one slot
to_bytes() assembles in correct order:
    Legacy Prefix | REX | Opcode | ModRM | SIB | Displacement | Immediate
"""

class EncodedInstructions:
    def __init__(self):
        self.legacy_prefix = b""
        self.rex           = b""
        self.opcode        = b""
        self.modrm         = b""
        self.sib           = b""
        self.displacement  = b""
        self.immediate     = b""

    def to_bytes(self) -> bytes:
        total = (
            len(self.legacy_prefix) +
            len(self.rex)           +
            len(self.opcode)        +
            len(self.modrm)         +
            len(self.sib)           +
            len(self.displacement)  +
            len(self.immediate)
        )
        if total > 15:
            raise EncoderError(
                f"instruction exceeds 15 byte limit: {total} bytes"
            )
        return (
            self.legacy_prefix +
            self.rex           +
            self.opcode        +
            self.modrm         +
            self.sib           +
            self.displacement  +
            self.immediate
        )

    def __repr__(self):
        return f"Encoded({self.to_bytes().hex()})"


# alias so tests can import either name
EncodedInstruction = EncodedInstructions


# **** Encoding Each Slot ****

def encode_legacy_prefix(
    operand_size_override: bool = False,
    address_size_override: bool = False,   # ← rename from address_size
    lock:  bool = False,
    rep:   bool = False,
    repne: bool = False,
) -> bytes:
    prefix = b""
    if lock:                  prefix += b"\xF0"
    if repne:                 prefix += b"\xF2"
    if rep:                   prefix += b"\xF3"
    if operand_size_override: prefix += b"\x66"
    if address_size_override: prefix += b"\x67"   # ← rename here too
    return prefix

def encode_rex(
    w: bool = False,   # 64-bit operand size       — bit 3 → 0x08
    r: bool = False,   # extends ModRM reg field   — bit 2 → 0x04
    x: bool = False,   # extends SIB index field   — bit 1 → 0x02
    b: bool = False,   # extends ModRM r/m or base — bit 0 → 0x01
) -> bytes:
    # fix 1: was not([w,r,x,b]) which never returned True
    if not any([w, r, x, b]):
        return b""
    byte = 0x40         # 0100 0000 — REX base
    # fix 2: W was 0x80 (wrong bit), correct is 0x08
    if w: byte |= 0x08
    if r: byte |= 0x04
    if x: byte |= 0x02
    if b: byte |= 0x01
    return bytes([byte])


def encode_modrm(mod: int, reg: int, rm: int) -> bytes:
    """
    mod : 2 bits  00=mem  01=mem+disp8  10=mem+disp32  11=reg
    reg : 3 bits  register or opcode extension /0-/7
    rm  : 3 bits  register or memory base
    """
    assert 0 <= mod <= 3, f"mod out of range: {mod}"
    assert 0 <= reg <= 7, f"reg out of range: {reg}"
    assert 0 <= rm  <= 7, f"rm out of range: {rm}"
    return bytes([(mod << 6) | (reg << 3) | rm])


def encode_sib(scale: int, index: int, base: int) -> bytes:
    """
    scale: 1/2/4/8 → encoded as 0/1/2/3
    index: 3 bits
    base:  3 bits
    """
    scale_enc = {1: 0, 2: 1, 4: 2, 8: 3}
    if scale not in scale_enc:
        raise EncoderError(f"invalid SIB scale: {scale}")
    return bytes([(scale_enc[scale] << 6) | (index << 3) | base])


def encode_displacement(value: int, size: int) -> bytes:
    """
    size: 0=none  1=8bit  4=32bit
    """
    if size == 0: return b""
    if size == 1: return struct.pack("<b", value)
    if size == 4: return struct.pack("<i", value)
    raise EncoderError(f"invalid displacement size: {size}")


def encode_immediate(value: int, size: int) -> bytes:
    # unsigned formats for encoding raw bytes
    fmts = {1: "<B", 2: "<H", 4: "<I", 8: "<Q"}
    if size not in fmts:
        raise EncoderError(f"invalid immediate size: {size}")
    # mask to correct width to handle negative values too
    masks = {1: 0xFF, 2: 0xFFFF, 4: 0xFFFFFFFF, 8: 0xFFFFFFFFFFFFFFFF}
    return struct.pack(fmts[size], value & masks[size])



# **** Memory Operand Helper ****

def _encode_memory(
    result:    EncodedInstructions,
    reg_field: int,                 # reg field in ModRM
    mem_op:    Operand,             # the memory operand
    is_64:     bool = False,
) -> None:
    """
    fills result.modrm, result.sib, result.displacement
    for a memory operand [base + index*scale + disp]
    """
    base  = mem_op.base
    index = mem_op.index
    scale = mem_op.scale
    disp  = mem_op.disp

    # REX extensions for memory operand registers
    rex_b = _is_extended(base)  if base  else False
    rex_x = _is_extended(index) if index else False
    if rex_b or rex_x:
        old_rex = result.rex
        w = bool(old_rex and (old_rex[0] & 0x08))
        r = bool(old_rex and (old_rex[0] & 0x04))
        result.rex = encode_rex(w=w, r=r, x=rex_x, b=rex_b)

    base_enc  = (_reg_num(base)  & 0x7) if base  else 0
    index_enc = (_reg_num(index) & 0x7) if index else 0

    # RIP relative — mod=00, r/m=101, 32-bit displacement
    if base and base.upper() == "RIP":
        result.modrm       = encode_modrm(0b00, reg_field, 0b101)
        result.displacement = encode_displacement(disp, 4)
        return

    # no base, has index — SIB with no base
    if base is None and index is not None:
        result.modrm       = encode_modrm(0b00, reg_field, 0b100)
        result.sib         = encode_sib(scale, index_enc, 0b101)
        result.displacement = encode_displacement(disp, 4)
        return

    # no base, no index — direct address
    if base is None and index is None:
        result.modrm       = encode_modrm(0b00, reg_field, 0b101)
        result.displacement = encode_displacement(disp, 4)
        return

    # needs SIB — base=ESP/RSP/R12 or has index
    needs_sib = (
        index is not None or
        (base and base.upper() in ("ESP", "RSP", "R12", "R12D"))
    )

    if needs_sib:
        idx = index_enc if index else 0b100   # 100 = no index
        sib = encode_sib(scale if index else 1, idx, base_enc)
    else:
        sib = b""

    # choose mod based on displacement size
    if disp == 0 and base and base.upper() not in ("EBP","RBP","R13","R13D"):
        mod       = 0b00
        disp_size = 0
    elif -128 <= disp <= 127:
        mod       = 0b01
        disp_size = 1
    else:
        mod       = 0b10
        disp_size = 4

    rm = 0b100 if needs_sib else base_enc

    result.modrm       = encode_modrm(mod, reg_field, rm)
    result.sib         = sib
    result.displacement = encode_displacement(disp, disp_size)


# **** Instruction Encoders ****

# fix 3: _encode_nop was missing _instr, _sym parameters
def _encode_nop(_instr, _sym) -> bytes:
    return b"\x90"


def _encode_ret(_instr, _sym) -> bytes:
    return b"\xC3"


def _encode_hlt(_instr, _sym) -> bytes:
    return b"\xF4"


def _encode_syscall(_instr, _sym) -> bytes:
    return b"\x0F\x05"


def _encode_push(instr: IRInstructions, sym: SymbolTable) -> bytes:
    op     = instr.operands[0]
    result = EncodedInstructions()

    if op.op_type == OperandType.REGISTER:
        reg = op.value.upper()
        num = _reg_num(reg)

        if _is_64bit(reg):
            if num >= 8:
                result.rex = encode_rex(b=True)
            result.opcode = bytes([0x50 + (num & 0x7)])

        elif _is_16bit(reg):
            result.legacy_prefix = b"\x66"
            result.opcode        = bytes([0x50 + (num & 0x7)])

        else:
            result.opcode = bytes([0x50 + (num & 0x7)])

    elif op.op_type == OperandType.IMMEDIATE:
        v = op.value
        if -128 <= v <= 127:
            result.opcode    = b"\x6A"
            result.immediate = encode_immediate(v, 1)
        else:
            result.opcode    = b"\x68"
            result.immediate = encode_immediate(v, 4)

    return result.to_bytes()


def _encode_pop(instr: IRInstructions, sym: SymbolTable) -> bytes:
    op     = instr.operands[0]
    result = EncodedInstructions()

    if op.op_type == OperandType.REGISTER:
        reg = op.value.upper()
        num = _reg_num(reg)

        if _is_64bit(reg):
            if num >= 8:
                result.rex = encode_rex(b=True)
            result.opcode = bytes([0x58 + (num & 0x7)])

        elif _is_16bit(reg):
            result.legacy_prefix = b"\x66"
            result.opcode        = bytes([0x58 + (num & 0x7)])

        else:
            result.opcode = bytes([0x58 + (num & 0x7)])

    return result.to_bytes()


def _encode_mov(instr: IRInstructions, sym: SymbolTable) -> bytes:
    dst    = instr.operands[0]
    src    = instr.operands[1]
    result = EncodedInstructions()

    # MOV reg, reg
    if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.REGISTER:
        d = dst.value.upper()
        s = src.value.upper()

        if _is_64bit(d):
            result.rex   = encode_rex(w=True, r=_is_extended(s), b=_is_extended(d))
            result.opcode = b"\x89"
            result.modrm  = encode_modrm(0b11, _reg_enc(s), _reg_enc(d))
        elif _is_32bit(d):
            if _is_extended(s) or _is_extended(d):
                result.rex = encode_rex(r=_is_extended(s), b=_is_extended(d))
            result.opcode = b"\x89"
            result.modrm  = encode_modrm(0b11, _reg_enc(s), _reg_enc(d))
        elif _is_16bit(d):
            result.legacy_prefix = b"\x66"
            result.opcode        = b"\x89"
            result.modrm         = encode_modrm(0b11, _reg_enc(s), _reg_enc(d))
        elif _is_8bit(d):
            result.opcode = b"\x88"
            result.modrm  = encode_modrm(0b11, _reg_enc(s), _reg_enc(d))

        return result.to_bytes()

    # MOV reg, imm
    if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.IMMEDIATE:
        d   = dst.value.upper()
        num = _reg_num(d)
        v   = src.value

        if _is_64bit(d):
            result.rex       = encode_rex(w=True, b=_is_extended(d))
            result.opcode    = bytes([0xB8 + (num & 0x7)])
            result.immediate = encode_immediate(v, 8)
        elif _is_32bit(d):
            if _is_extended(d):
                result.rex = encode_rex(b=True)
            result.opcode    = bytes([0xB8 + (num & 0x7)])
            result.immediate = encode_immediate(v, 4)
        elif _is_16bit(d):
            result.legacy_prefix = b"\x66"
            result.opcode        = bytes([0xB8 + (num & 0x7)])
            result.immediate     = encode_immediate(v, 2)
        elif _is_8bit(d):
            result.opcode    = bytes([0xB0 + (num & 0x7)])
            result.immediate = encode_immediate(v, 1)

        return result.to_bytes()

    # MOV reg, mem
    if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.MEMORY:
        d = dst.value.upper()

        if _is_64bit(d):
            result.rex    = encode_rex(w=True, r=_is_extended(d))
            result.opcode = b"\x8B"
        elif _is_32bit(d):
            if _is_extended(d):
                result.rex = encode_rex(r=True)
            result.opcode = b"\x8B"
        elif _is_16bit(d):
            result.legacy_prefix = b"\x66"
            result.opcode        = b"\x8B"
        elif _is_8bit(d):
            result.opcode = b"\x8A"

        _encode_memory(result, _reg_enc(d), src)
        return result.to_bytes()

    # MOV mem, reg
    if dst.op_type == OperandType.MEMORY and src.op_type == OperandType.REGISTER:
        s = src.value.upper()

        if _is_64bit(s):
            result.rex    = encode_rex(w=True, r=_is_extended(s))
            result.opcode = b"\x89"
        elif _is_32bit(s):
            if _is_extended(s):
                result.rex = encode_rex(r=True)
            result.opcode = b"\x89"
        elif _is_16bit(s):
            result.legacy_prefix = b"\x66"
            result.opcode        = b"\x89"
        elif _is_8bit(s):
            result.opcode = b"\x88"

        _encode_memory(result, _reg_enc(s), dst)
        return result.to_bytes()

    # MOV mem, imm
    if dst.op_type == OperandType.MEMORY and src.op_type == OperandType.IMMEDIATE:
        v    = src.value
        hint = dst.size

        if hint == OperandSize.QWORD:
            result.rex    = encode_rex(w=True)
            result.opcode = b"\xC7"
            _encode_memory(result, 0, dst)
            result.immediate = encode_immediate(v, 4)
        elif hint == OperandSize.DWORD:
            result.opcode = b"\xC7"
            _encode_memory(result, 0, dst)
            result.immediate = encode_immediate(v, 4)
        elif hint == OperandSize.WORD:
            result.legacy_prefix = b"\x66"
            result.opcode        = b"\xC7"
            _encode_memory(result, 0, dst)
            result.immediate     = encode_immediate(v, 2)
        elif hint == OperandSize.BYTE:
            result.opcode = b"\xC6"
            _encode_memory(result, 0, dst)
            result.immediate = encode_immediate(v, 1)

        return result.to_bytes()

    raise EncoderError(
        f"[line {instr.line}] MOV: unsupported operand combination "
        f"{dst.op_type} {src.op_type}"
    )


def _encode_alu(instr: IRInstructions, sym: SymbolTable) -> bytes:
    """
    handles ADD SUB AND OR XOR CMP
    all share the same ModRM pattern
    """
    mnemonic = instr.mnemonic
    dst      = instr.operands[0]
    src      = instr.operands[1]
    result   = EncodedInstructions()

    #           r/m32←r32  r32←r/m32  /digit  eax←imm32
    op_map = {
        "ADD": (b"\x01", b"\x03", 0, b"\x05"),
        "SUB": (b"\x29", b"\x2B", 5, b"\x2D"),
        "AND": (b"\x21", b"\x23", 4, b"\x25"),
        "OR":  (b"\x09", b"\x0B", 1, b"\x0D"),
        "XOR": (b"\x31", b"\x33", 6, b"\x35"),
        "CMP": (b"\x39", b"\x3B", 7, b"\x3D"),
    }

    if mnemonic not in op_map:
        raise EncoderError(f"_encode_alu called with {mnemonic}")

    op_rm_r, op_r_rm, imm_digit, _ = op_map[mnemonic]

    # reg, reg
    if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.REGISTER:
        d = dst.value.upper()
        s = src.value.upper()

        if _is_64bit(d):
            result.rex    = encode_rex(w=True, r=_is_extended(s), b=_is_extended(d))
            result.opcode = op_rm_r
            result.modrm  = encode_modrm(0b11, _reg_enc(s), _reg_enc(d))
        elif _is_32bit(d):
            if _is_extended(s) or _is_extended(d):
                result.rex = encode_rex(r=_is_extended(s), b=_is_extended(d))
            result.opcode = op_rm_r
            result.modrm  = encode_modrm(0b11, _reg_enc(s), _reg_enc(d))
        elif _is_16bit(d):
            result.legacy_prefix = b"\x66"
            result.opcode        = op_rm_r
            result.modrm         = encode_modrm(0b11, _reg_enc(s), _reg_enc(d))
        elif _is_8bit(d):
            # 8-bit form opcode is always one less than 32-bit form
            result.opcode = bytes([op_rm_r[0] - 1])
            result.modrm  = encode_modrm(0b11, _reg_enc(s), _reg_enc(d))

        return result.to_bytes()

    # reg, imm
    if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.IMMEDIATE:
        d = dst.value.upper()
        v = src.value

        if _is_64bit(d):
            result.rex = encode_rex(w=True, b=_is_extended(d))
            if -128 <= v <= 255:
                result.opcode    = b"\x83"
                result.modrm     = encode_modrm(0b11, imm_digit, _reg_enc(d))
                result.immediate = encode_immediate(v, 1)
            else:
                result.opcode    = b"\x81"
                result.modrm     = encode_modrm(0b11, imm_digit, _reg_enc(d))
                result.immediate = encode_immediate(v, 4)
        elif _is_32bit(d):
            if _is_extended(d):
                result.rex = encode_rex(b=True)
            if -128 <= v <= 255:
                result.opcode    = b"\x83"
                result.modrm     = encode_modrm(0b11, imm_digit, _reg_enc(d))
                result.immediate = encode_immediate(v, 1)
            else:
                result.opcode    = b"\x81"
                result.modrm     = encode_modrm(0b11, imm_digit, _reg_enc(d))
                result.immediate = encode_immediate(v, 4)
        elif _is_16bit(d):
            result.legacy_prefix = b"\x66"
            result.opcode        = b"\x81"
            result.modrm         = encode_modrm(0b11, imm_digit, _reg_enc(d))
            result.immediate     = encode_immediate(v, 2)
        elif _is_8bit(d):
            result.opcode    = b"\x80"
            result.modrm     = encode_modrm(0b11, imm_digit, _reg_enc(d))
            result.immediate = encode_immediate(v, 1)

        return result.to_bytes()

    # reg, mem
    if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.MEMORY:
        d = dst.value.upper()

        if _is_64bit(d):
            result.rex    = encode_rex(w=True, r=_is_extended(d))
            result.opcode = op_r_rm
        elif _is_32bit(d):
            if _is_extended(d):
                result.rex = encode_rex(r=True)
            result.opcode = op_r_rm
        elif _is_16bit(d):
            result.legacy_prefix = b"\x66"
            result.opcode        = op_r_rm

        _encode_memory(result, _reg_enc(d), src)
        return result.to_bytes()

    # mem, reg
    if dst.op_type == OperandType.MEMORY and src.op_type == OperandType.REGISTER:
        s = src.value.upper()

        if _is_64bit(s):
            result.rex    = encode_rex(w=True, r=_is_extended(s))
            result.opcode = op_rm_r
        elif _is_32bit(s):
            if _is_extended(s):
                result.rex = encode_rex(r=True)
            result.opcode = op_rm_r
        elif _is_16bit(s):
            result.legacy_prefix = b"\x66"
            result.opcode        = op_rm_r
        elif _is_8bit(s):
            result.opcode = bytes([op_rm_r[0] - 1])

        _encode_memory(result, _reg_enc(s), dst)
        return result.to_bytes()

    raise EncoderError(
        f"[line {instr.line}] {mnemonic}: unsupported operand combination"
    )


def _encode_inc_dec(instr: IRInstructions, sym: SymbolTable) -> bytes:
    mnemonic = instr.mnemonic
    op       = instr.operands[0]
    result   = EncodedInstructions()
    digit    = 0 if mnemonic == "INC" else 1   # /0 for INC  /1 for DEC

    if op.op_type == OperandType.REGISTER:
        r = op.value.upper()

        if _is_64bit(r):
            result.rex    = encode_rex(w=True, b=_is_extended(r))
            result.opcode = b"\xFF"
            result.modrm  = encode_modrm(0b11, digit, _reg_enc(r))
        elif _is_32bit(r):
            if _is_extended(r):
                result.rex = encode_rex(b=True)
            result.opcode = b"\xFF"
            result.modrm  = encode_modrm(0b11, digit, _reg_enc(r))
        elif _is_16bit(r):
            result.legacy_prefix = b"\x66"
            result.opcode        = b"\xFF"
            result.modrm         = encode_modrm(0b11, digit, _reg_enc(r))
        elif _is_8bit(r):
            result.opcode = b"\xFE"
            result.modrm  = encode_modrm(0b11, digit, _reg_enc(r))

    return result.to_bytes()


def _encode_neg_not(instr: IRInstructions, sym: SymbolTable) -> bytes:
    mnemonic = instr.mnemonic
    op       = instr.operands[0]
    result   = EncodedInstructions()
    digit    = 3 if mnemonic == "NEG" else 2   # /3 for NEG  /2 for NOT

    if op.op_type == OperandType.REGISTER:
        r = op.value.upper()

        if _is_64bit(r):
            result.rex    = encode_rex(w=True, b=_is_extended(r))
            result.opcode = b"\xF7"
            result.modrm  = encode_modrm(0b11, digit, _reg_enc(r))
        elif _is_32bit(r):
            if _is_extended(r):
                result.rex = encode_rex(b=True)
            result.opcode = b"\xF7"
            result.modrm  = encode_modrm(0b11, digit, _reg_enc(r))
        elif _is_8bit(r):
            result.opcode = b"\xF6"
            result.modrm  = encode_modrm(0b11, digit, _reg_enc(r))

    return result.to_bytes()


def _encode_mul_div(instr: IRInstructions, sym: SymbolTable) -> bytes:
    mnemonic  = instr.mnemonic
    op        = instr.operands[0]
    result    = EncodedInstructions()

    digit_map = {"MUL": 4, "IMUL": 5, "DIV": 6, "IDIV": 7}
    digit     = digit_map[mnemonic]

    if op.op_type == OperandType.REGISTER:
        r = op.value.upper()

        if _is_64bit(r):
            result.rex    = encode_rex(w=True, b=_is_extended(r))
            result.opcode = b"\xF7"
            result.modrm  = encode_modrm(0b11, digit, _reg_enc(r))
        elif _is_32bit(r):
            if _is_extended(r):
                result.rex = encode_rex(b=True)
            result.opcode = b"\xF7"
            result.modrm  = encode_modrm(0b11, digit, _reg_enc(r))
        elif _is_8bit(r):
            result.opcode = b"\xF6"
            result.modrm  = encode_modrm(0b11, digit, _reg_enc(r))

    return result.to_bytes()


def _encode_shift(instr: IRInstructions, sym: SymbolTable) -> bytes:
    """handles SHL SHR SAR ROL ROR RCL RCR"""
    mnemonic = instr.mnemonic
    dst      = instr.operands[0]
    src      = instr.operands[1] if len(instr.operands) > 1 else None
    result   = EncodedInstructions()

    digit_map = {
        "ROL": 0, "ROR": 1, "RCL": 2, "RCR": 3,
        "SHL": 4, "SHR": 5, "SAR": 7,
    }
    digit  = digit_map.get(mnemonic, 4)
    r      = dst.value.upper()
    rm_enc = _reg_enc(r)

    if _is_64bit(r):
        result.rex = encode_rex(w=True, b=_is_extended(r))
        if src and src.op_type == OperandType.IMMEDIATE:
            v = src.value
            if v == 1:
                result.opcode = b"\xD1"
                result.modrm  = encode_modrm(0b11, digit, rm_enc)
            else:
                result.opcode    = b"\xC1"
                result.modrm     = encode_modrm(0b11, digit, rm_enc)
                result.immediate = encode_immediate(v, 1)
        else:
            result.opcode = b"\xD3"
            result.modrm  = encode_modrm(0b11, digit, rm_enc)

    elif _is_32bit(r):
        if _is_extended(r):
            result.rex = encode_rex(b=True)
        if src and src.op_type == OperandType.IMMEDIATE:
            v = src.value
            if v == 1:
                result.opcode = b"\xD1"
                result.modrm  = encode_modrm(0b11, digit, rm_enc)
            else:
                result.opcode    = b"\xC1"
                result.modrm     = encode_modrm(0b11, digit, rm_enc)
                result.immediate = encode_immediate(v, 1)
        else:
            result.opcode = b"\xD3"
            result.modrm  = encode_modrm(0b11, digit, rm_enc)

    return result.to_bytes()


def _encode_jmp(instr: IRInstructions, sym: SymbolTable, current_offset: int) -> bytes:
    """JMP — near relative 32-bit"""
    op     = instr.operands[0]
    result = EncodedInstructions()

    if op.op_type == OperandType.LABEL_REF:
        target = op.resolved_offset
        # rel32 = target - (current_offset + 5)
        # 5 = opcode(1) + rel32(4)
        rel32          = target - (current_offset + 5)
        result.opcode    = b"\xE9"
        result.immediate = struct.pack("<i", rel32)

    elif op.op_type == OperandType.REGISTER:
        r = op.value.upper()
        if _is_64bit(r) and _is_extended(r):
            result.rex = encode_rex(b=True)
        result.opcode = b"\xFF"
        result.modrm  = encode_modrm(0b11, 4, _reg_enc(r))

    return result.to_bytes()


def _encode_call(instr: IRInstructions, sym: SymbolTable, current_offset: int) -> bytes:
    """CALL — near relative 32-bit"""
    op     = instr.operands[0]
    result = EncodedInstructions()

    if op.op_type == OperandType.LABEL_REF:
        target = op.resolved_offset
        rel32          = target - (current_offset + 5)
        result.opcode    = b"\xE8"
        result.immediate = struct.pack("<i", rel32)

    elif op.op_type == OperandType.REGISTER:
        r = op.value.upper()
        result.opcode = b"\xFF"
        result.modrm  = encode_modrm(0b11, 2, _reg_enc(r))

    return result.to_bytes()


def _encode_jcc(instr: IRInstructions, sym: SymbolTable, current_offset: int) -> bytes:
    """conditional jumps — near 32-bit form"""
    mnemonic = instr.mnemonic
    op       = instr.operands[0]

    jcc_map = {
        "JO":  0x80, "JNO": 0x81, "JB":  0x82, "JNB": 0x83,
        "JE":  0x84, "JZ":  0x84, "JNE": 0x85, "JNZ": 0x85,
        "JBE": 0x86, "JA":  0x87, "JS":  0x88, "JNS": 0x89,
        "JP":  0x8A, "JNP": 0x8B, "JL":  0x8C, "JGE": 0x8D,
        "JLE": 0x8E, "JG":  0x8F,
    }

    if mnemonic not in jcc_map:
        raise EncoderError(f"unknown conditional jump: {mnemonic}")

    opcode2 = jcc_map[mnemonic]
    target  = op.resolved_offset
    # rel32 = target - (current_offset + 6)
    # 6 = opcode(2) + rel32(4)
    rel32   = target - (current_offset + 6)

    return b"\x0F" + bytes([opcode2]) + struct.pack("<i", rel32)


def _encode_loop(instr: IRInstructions, sym: SymbolTable, current_offset: int) -> bytes:
    """LOOP LOOPE LOOPNE — short form only (-128..127)"""
    mnemonic = instr.mnemonic
    op       = instr.operands[0]

    opcode_map = {"LOOP": 0xE2, "LOOPE": 0xE1, "LOOPNE": 0xE0}
    opcode     = opcode_map[mnemonic]
    target     = op.resolved_offset
    # rel8 = target - (current_offset + 2)
    rel8       = target - (current_offset + 2)

    if not (-128 <= rel8 <= 127):
        raise EncoderError(
            f"[line {instr.line}] {mnemonic} target out of short range: {rel8}"
        )

    return bytes([opcode]) + struct.pack("<b", rel8)


def _encode_data(node: IRData) -> bytes:
    """encode DB DW DD DQ RESB RESW RESD RESQ"""
    size_bytes = {
        OperandSize.BYTE:  1,
        OperandSize.WORD:  2,
        OperandSize.DWORD: 4,
        OperandSize.QWORD: 8,
    }
    unit = size_bytes.get(node.size, 1)
    out  = b""

    if node.is_reserve:
        # RESB/RESW/RESD/RESQ — emit count * unit zero bytes
        for v in node.values:
            if isinstance(v, int):
                out += b"\x00" * (unit * v)
        return out

    # DB/DW/DD/DQ — emit actual values
    fmt_map = {1: "<B", 2: "<H", 4: "<I", 8: "<Q"}
    fmt     = fmt_map.get(unit, "<B")

    for v in node.values:
        if isinstance(v, str):
            out += v.encode("utf-8")
        elif isinstance(v, int):
            out += struct.pack(fmt, v & ((1 << (unit * 8)) - 1))

    return out


# **** Dispatch Tables ****

_JUMP_MNEMONICS = {
    "JMP", "CALL",
    "JO",  "JNO", "JB",  "JNB", "JE",  "JZ",
    "JNE", "JNZ", "JBE", "JA",  "JS",  "JNS",
    "JP",  "JNP", "JL",  "JGE", "JLE", "JG",
    "LOOP","LOOPE","LOOPNE",
}

_ALU_MNEMONICS   = {"ADD", "SUB", "AND", "OR", "XOR", "CMP"}
_SHIFT_MNEMONICS = {"SHL", "SHR", "SAR", "ROL", "ROR", "RCL", "RCR"}

_SIMPLE = {
    "NOP":     _encode_nop,
    "RET":     _encode_ret,
    "HLT":     _encode_hlt,
    "SYSCALL": _encode_syscall,
}

_ONE_OP = {
    "PUSH":  _encode_push,
    "POP":   _encode_pop,
    "INC":   _encode_inc_dec,
    "DEC":   _encode_inc_dec,
    "NEG":   _encode_neg_not,
    "NOT":   _encode_neg_not,
    "MUL":   _encode_mul_div,
    "IMUL":  _encode_mul_div,
    "DIV":   _encode_mul_div,
    "IDIV":  _encode_mul_div,
}


# **** Main Encoder ****

class Encoder:
    def __init__(self, program: IRProgram, sym_table: SymbolTable):
        self.program   = program
        self.sym_table = sym_table
        self.output    = b""
        self.offset    = sym_table.base_address

    def encode(self) -> bytes:
        """walk all IR nodes and encode to bytes"""
        for node in self.program.nodes:

            if isinstance(node, IRInstructions):
                encoded        = self._encode_instruction(node)
                node.enc_bytes = encoded
                self.output   += encoded
                self.offset   += len(encoded)

            elif isinstance(node, IRData):
                encoded      = _encode_data(node)
                self.output += encoded
                self.offset += len(encoded)

            elif isinstance(node, IRLabel):
                pass   # labels produce no bytes

            elif isinstance(node, IRDirectives):
                pass   # handled by symbol table

        return self.output

    def _encode_instruction(self, instr: IRInstructions) -> bytes:
        mnemonic = instr.mnemonic

        if mnemonic in _SIMPLE:
            return _SIMPLE[mnemonic](instr, self.sym_table)

        if mnemonic in _ONE_OP:
            return _ONE_OP[mnemonic](instr, self.sym_table)

        if mnemonic == "MOV":
            return _encode_mov(instr, self.sym_table)

        if mnemonic in _ALU_MNEMONICS:
            return _encode_alu(instr, self.sym_table)

        if mnemonic in _SHIFT_MNEMONICS:
            return _encode_shift(instr, self.sym_table)

        if mnemonic in _JUMP_MNEMONICS:
            return self._encode_jump(instr)

        raise EncoderError(
            f"[line {instr.line}] unsupported mnemonic: '{mnemonic}'"
        )

    def _encode_jump(self, instr: IRInstructions) -> bytes:
        mnemonic = instr.mnemonic

        if mnemonic == "JMP":
            return _encode_jmp(instr, self.sym_table, self.offset)

        if mnemonic == "CALL":
            return _encode_call(instr, self.sym_table, self.offset)

        if mnemonic in ("LOOP", "LOOPE", "LOOPNE"):
            return _encode_loop(instr, self.sym_table, self.offset)

        return _encode_jcc(instr, self.sym_table, self.offset)