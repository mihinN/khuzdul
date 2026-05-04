# assembler/symbol_table.py
#
# two-pass symbol resolution
#   pass 1 :  walk nodes, accumulate offset, record label -> offset
#   pass 2 :  walk instructions, resolve every LABEL_REF operand
#
# size estimation in pass 1 uses the same logic the encoder will use, so
# offsets agree.  no jump-shortening — we always assume the long form
# (rel32) for jumps/calls and rel8 for LOOP/LOOPNE/LOOPE.
#
# all label names are normalised to UPPER CASE.  the parser already
# uppercases LABEL_REF values; we uppercase IRLabel.name on insertion.

from assembler.error import AssemblerError, SymbolError
from assembler.ir    import (
    IRData, IRDirectives, IRInstructions, IRLabel,
    Operand, OperandType, OperandSize,
)


# **** Errors ****

class DuplicateLabelError(SymbolError):
    """raised when the same label is defined twice"""
    pass


class UndefinedLabelError(SymbolError):
    """raised when a LABEL_REF cannot be resolved"""
    pass


# **** Symbol record ****

class Symbol:
    def __init__(
        self,
        name: str,
        offset: int = 0,
        is_global: bool = False,
        is_extern: bool = False,
        is_local: bool = False,
        line: int = 0,
    ):
        self.name      = name
        self.offset    = offset
        self.is_global = is_global
        self.is_extern = is_extern
        self.is_local  = is_local
        self.line      = line

    def __repr__(self):
        return f"Symbol({self.name!r}, offset=0x{self.offset:04X})"


# **** Size estimator ****
#
# kept in sync with encoder.  for any instruction whose encoded length
# depends on the destination's register size, we look at the operand
# sizes the parser already filled in.  for label-targeted control flow
# we always reserve the long form so offsets don't shift in pass 2.

# sizes for no-operand instructions
_FIXED_SIZE = {
    "NOP":     1,
    "RET":     1,
    "HLT":     1,
    "SYSCALL": 2,
    "PUSHF":   1,
    "POPF":    1,
    "PUSHFQ":  1,
    "POPFQ":   1,
    "CDQ":     1,
    "CWD":     1,
    "CQO":     2,   # REX.W + 99
    "LEAVE":   1,
    "INT3":    1,
}

_JCC_NEAR = {
    "JO","JNO","JB","JNB","JC","JNC","JE","JZ","JNE","JNZ",
    "JBE","JA","JNA","JAE","JS","JNS","JP","JNP","JL","JGE","JLE","JG",
}

_LOOP_SHORT = {"LOOP", "LOOPE", "LOOPNE"}

_ALU_2OP = {"ADD","SUB","AND","OR","XOR","CMP","ADC","SBB"}


def _reg_size_bytes(reg_name: str) -> int:
    """rough lookup; falls back to 4 if unknown.  used only for sizing."""
    if not reg_name:
        return 4
    r = reg_name.upper()
    if r in {"AL","AH","BL","BH","CL","CH","DL","DH",
             "SIL","DIL","BPL","SPL",
             "R8B","R9B","R10B","R11B","R12B","R13B","R14B","R15B"}:
        return 1
    if r in {"AX","BX","CX","DX","SI","DI","SP","BP",
             "R8W","R9W","R10W","R11W","R12W","R13W","R14W","R15W"}:
        return 2
    if r.startswith("E") or r in {"R8D","R9D","R10D","R11D",
                                  "R12D","R13D","R14D","R15D"}:
        return 4
    if r.startswith("R"):
        return 8
    return 4


def _is_extended_reg(reg_name: str) -> bool:
    if not reg_name:
        return False
    r = reg_name.upper()
    if r in {"R8","R9","R10","R11","R12","R13","R14","R15"}:
        return True
    if r.startswith("R") and r.endswith(("B","W","D")) and r[1:-1].isdigit():
        return True
    return False


def _imm_byte_size(value: int, dst_bytes: int) -> int:
    """
    return how many bytes the immediate occupies after the opcode.
    only handles ALU-style (sign-extended imm8 vs full-width imm) for now.
    """
    if dst_bytes == 1:
        return 1
    # signed 8-bit fits → \x83 form  (1-byte imm)
    if -128 <= value <= 127:
        return 1
    return 4 if dst_bytes >= 4 else 2


def _size_memory_operand(mem: Operand) -> int:
    """ModRM(1) + optional SIB(1) + optional displacement(0/1/4)."""
    size = 1   # ModRM
    base  = (mem.base  or "").upper()
    index = (mem.index or "").upper()
    disp  = mem.disp

    # RIP relative — always 4-byte displacement
    if base == "RIP":
        return 1 + 4

    needs_sib = (
        index is not None and index != "" or
        base in {"ESP","RSP","R12","R12D"}
    )
    if needs_sib:
        size += 1

    # displacement-only (no base, no index)
    if base == "" and index == "":
        return 1 + 4

    if disp == 0 and base not in {"EBP","RBP","R13","R13D"}:
        pass    # no displacement
    elif -128 <= disp <= 127:
        size += 1
    else:
        size += 4

    return size


def _estimate_instr_size(instr: IRInstructions) -> int:
    m  = instr.mnemonic
    ops = instr.operands

    if m in _FIXED_SIZE:
        return _FIXED_SIZE[m]

    # control flow with label
    if m in {"JMP", "CALL"}:
        if ops and ops[0].op_type == OperandType.LABEL_REF:
            return 5    # opcode(1) + rel32(4)
        if ops and ops[0].op_type == OperandType.REGISTER:
            r = ops[0].value.upper()
            return (1 if not _is_extended_reg(r) else 2) + 1   # [REX]+FF+ModRM
        return 5

    if m in _JCC_NEAR:
        return 6        # 0F + opcode + rel32

    if m in _LOOP_SHORT:
        return 2        # opcode + rel8

    # PUSH / POP — single operand register
    if m in {"PUSH", "POP"}:
        if ops and ops[0].op_type == OperandType.REGISTER:
            r = ops[0].value.upper()
            sz = _reg_size_bytes(r)
            extra = 1 if _is_extended_reg(r) else 0
            prefix = 1 if sz == 2 else 0
            return prefix + extra + 1   # opcode is 1 byte
        if ops and ops[0].op_type == OperandType.IMMEDIATE:
            return 2 if -128 <= ops[0].value <= 127 else 5
        if ops and ops[0].op_type == OperandType.MEMORY:
            return 1 + _size_memory_operand(ops[0])

    # INC / DEC / NEG / NOT / MUL / IMUL / DIV / IDIV
    if m in {"INC","DEC","NEG","NOT","MUL","IMUL","DIV","IDIV"}:
        if ops and ops[0].op_type == OperandType.REGISTER:
            r = ops[0].value.upper()
            sz = _reg_size_bytes(r)
            rex = 1 if (sz == 8 or _is_extended_reg(r)) else 0
            pre = 1 if sz == 2 else 0
            return pre + rex + 1 + 1   # opcode + ModRM

    # MOV
    if m == "MOV" and len(ops) == 2:
        dst, src = ops
        # MOV reg, reg
        if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.REGISTER:
            sz = _reg_size_bytes(dst.value)
            rex = 1 if (sz == 8 or
                        _is_extended_reg(dst.value) or
                        _is_extended_reg(src.value)) else 0
            pre = 1 if sz == 2 else 0
            return pre + rex + 1 + 1

        # MOV reg, imm
        if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.IMMEDIATE:
            sz = _reg_size_bytes(dst.value)
            rex = 1 if (sz == 8 or _is_extended_reg(dst.value)) else 0
            pre = 1 if sz == 2 else 0
            return pre + rex + 1 + sz

        # MOV reg, label_ref  (we treat as MOV r64, imm64 — 10 bytes for r64)
        if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.LABEL_REF:
            sz = _reg_size_bytes(dst.value)
            rex = 1 if (sz == 8 or _is_extended_reg(dst.value)) else 0
            pre = 1 if sz == 2 else 0
            return pre + rex + 1 + sz

        # MOV reg, mem  /  MOV mem, reg
        if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.MEMORY:
            sz  = _reg_size_bytes(dst.value)
            rex = 1 if (sz == 8 or _is_extended_reg(dst.value)) else 0
            pre = 1 if sz == 2 else 0
            return pre + rex + 1 + _size_memory_operand(src)

        if dst.op_type == OperandType.MEMORY and src.op_type == OperandType.REGISTER:
            sz  = _reg_size_bytes(src.value)
            rex = 1 if (sz == 8 or _is_extended_reg(src.value)) else 0
            pre = 1 if sz == 2 else 0
            return pre + rex + 1 + _size_memory_operand(dst)

        # MOV mem, imm
        if dst.op_type == OperandType.MEMORY and src.op_type == OperandType.IMMEDIATE:
            hint = dst.size
            sz   = {OperandSize.BYTE:1, OperandSize.WORD:2,
                    OperandSize.DWORD:4, OperandSize.QWORD:8}.get(hint, 4)
            rex  = 1 if sz == 8 else 0
            pre  = 1 if sz == 2 else 0
            imm  = 4 if sz >= 4 else sz
            return pre + rex + 1 + _size_memory_operand(dst) + imm

    # ALU 2-operand
    if m in _ALU_2OP and len(ops) == 2:
        dst, src = ops
        # reg, reg
        if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.REGISTER:
            sz = _reg_size_bytes(dst.value)
            rex = 1 if (sz == 8 or
                        _is_extended_reg(dst.value) or
                        _is_extended_reg(src.value)) else 0
            pre = 1 if sz == 2 else 0
            return pre + rex + 1 + 1

        # reg, imm
        if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.IMMEDIATE:
            sz  = _reg_size_bytes(dst.value)
            rex = 1 if (sz == 8 or _is_extended_reg(dst.value)) else 0
            pre = 1 if sz == 2 else 0
            imm = _imm_byte_size(src.value, sz)
            return pre + rex + 1 + 1 + imm

        # reg, mem
        if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.MEMORY:
            sz  = _reg_size_bytes(dst.value)
            rex = 1 if (sz == 8 or _is_extended_reg(dst.value)) else 0
            pre = 1 if sz == 2 else 0
            return pre + rex + 1 + _size_memory_operand(src)

        # mem, reg
        if dst.op_type == OperandType.MEMORY and src.op_type == OperandType.REGISTER:
            sz  = _reg_size_bytes(src.value)
            rex = 1 if (sz == 8 or _is_extended_reg(src.value)) else 0
            pre = 1 if sz == 2 else 0
            return pre + rex + 1 + _size_memory_operand(dst)

    # TEST — same shape as ALU but no /digit imm short form
    if m == "TEST" and len(ops) == 2:
        dst, src = ops
        if dst.op_type == OperandType.REGISTER and src.op_type == OperandType.REGISTER:
            sz = _reg_size_bytes(dst.value)
            rex = 1 if sz == 8 else 0
            pre = 1 if sz == 2 else 0
            return pre + rex + 1 + 1

    # SHL/SHR/SAR/ROL/ROR/RCL/RCR
    if m in {"SHL","SHR","SAR","ROL","ROR","RCL","RCR"} and ops:
        dst = ops[0]
        if dst.op_type == OperandType.REGISTER:
            sz  = _reg_size_bytes(dst.value)
            rex = 1 if (sz == 8 or _is_extended_reg(dst.value)) else 0
            pre = 1 if sz == 2 else 0
            base = 1 + 1   # opcode + ModRM
            if len(ops) == 2 and ops[1].op_type == OperandType.IMMEDIATE:
                if ops[1].value == 1:
                    return pre + rex + base
                return pre + rex + base + 1   # imm8
            return pre + rex + base   # CL form

    # fall-through — best-effort default
    return 4


def _data_size_bytes(node: IRData) -> int:
    unit = {OperandSize.BYTE:1, OperandSize.WORD:2,
            OperandSize.DWORD:4, OperandSize.QWORD:8}.get(node.size, 1)
    if node.is_reserve:
        total = 0
        for v in node.values:
            if isinstance(v, int):
                total += unit * v
        return total
    total = 0
    for v in node.values:
        if isinstance(v, str):
            total += len(v.encode("utf-8"))
        elif isinstance(v, int):
            total += unit
    return total


# **** SymbolTable ****

class SymbolTable:
    def __init__(self, base_address: int = 0):
        self.base_address = base_address
        self.symbols      = {}     # name (UPPER) -> Symbol
        self.globals      = set()
        self.externs      = set()

    # **** public API ****

    def build(self, program):
        """run pass 1 then pass 2."""
        self._pass1(program)
        self._pass2(program)

    def lookup(self, name: str) -> Symbol:
        key = name.upper()
        if key not in self.symbols:
            raise UndefinedLabelError(f"undefined label: {name}")
        return self.symbols[key]

    def offset_of(self, name: str) -> int:
        return self.lookup(name).offset

    def dump(self):
        print("=" * 60)
        print("  SYMBOL TABLE")
        print("=" * 60)
        for name, s in self.symbols.items():
            kind = []
            if s.is_global: kind.append("GLOBAL")
            if s.is_extern: kind.append("EXTERN")
            if s.is_local : kind.append("LOCAL")
            print(f"  {name:<20}  0x{s.offset:08X}  {' '.join(kind)}")
        print("=" * 60)

    # **** pass 1 ****

    def _pass1(self, program):
        """
        walk nodes in order.  for every IRLabel, register a Symbol at the
        current offset.  for every IRInstruction / IRData, advance the
        offset by the estimated size.

        also handles directives that affect the address space:
            ORG <n>           — set base_address (only valid before any code)
            GLOBAL <name>     — mark symbol global
            EXTERN <name>     — register an extern symbol at offset 0
        """
        offset = self.base_address

        for node in program.nodes:

            if isinstance(node, IRDirectives):
                name = node.name.upper()
                if name == "ORG" and node.args:
                    self.base_address = int(node.args[0])
                    offset = self.base_address
                elif name == "GLOBAL":
                    for a in node.args:
                        self.globals.add(str(a).upper())
                elif name == "EXTERN":
                    for a in node.args:
                        sym_name = str(a).upper()
                        self.externs.add(sym_name)
                        if sym_name not in self.symbols:
                            self.symbols[sym_name] = Symbol(
                                name=sym_name, offset=0, is_extern=True,
                            )
                # other directives don't change the address
                continue

            if isinstance(node, IRLabel):
                key = node.name.upper()
                if key in self.symbols and not self.symbols[key].is_extern:
                    raise DuplicateLabelError(
                        f"duplicate label: {node.name}",
                        line=node.line,
                    )
                node.offset = offset
                self.symbols[key] = Symbol(
                    name      = key,
                    offset    = offset,
                    is_local  = node.is_local,
                    line      = node.line,
                )
                continue

            if isinstance(node, IRInstructions):
                offset += _estimate_instr_size(node)
                continue

            if isinstance(node, IRData):
                offset += _data_size_bytes(node)
                continue

        # apply globals after all labels are known
        for g in self.globals:
            if g in self.symbols:
                self.symbols[g].is_global = True

    # **** pass 2 ****

    def _pass2(self, program):
        """resolve every LABEL_REF operand to its target offset."""
        for instr in program.instructions():
            for op in instr.operands:
                if op.op_type != OperandType.LABEL_REF:
                    continue
                key = op.value.upper()
                if key not in self.symbols:
                    raise UndefinedLabelError(
                        f"undefined label: {op.value}",
                        line=instr.line,
                    )
                op.resolved_offset = self.symbols[key].offset