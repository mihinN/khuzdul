from assembler.ir import (
    IRProgram, IRInstructions, IRLabel, IRDirectives, IRData,
    Operand, OperandType, OperandSize,
)


# **** Errors ****
class SymbolError(Exception):
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(
            f"[line {line}] SymbolError: {message}"
        )


class DuplicateLabelError(SymbolError):
    pass


class UndefinedLabelError(SymbolError):
    pass


# **** Symbol ****
class Symbol:
    def __init__(
        self,
        name:      str,
        offset:    int  = 0,        # byte offset in output
        is_global: bool = False,    # exported via GLOBAL directive
        is_extern: bool = False,    # imported via EXTERN directive
        is_local:  bool = False,    # starts with "." 
        line:      int  = 0,
    ):
        self.name      = name
        self.offset    = offset
        self.is_global = is_global
        self.is_extern = is_extern
        self.is_local  = is_local
        self.line      = line

    def __repr__(self):
        return (
            f"Symbol("
            f"name={self.name!r}, "
            f"offset=0x{self.offset:04X}, "
            f"global={self.is_global}, "
            f"extern={self.is_extern}, "
            f"local={self.is_local}"
            f")"
        )


# **** Estimator ****
# rough byte size estimator for pass 1
# encoder fills exact sizes in pass 2
# this is good enough for offset calculation

def _estimate_instruction_size(instr: IRInstructions) -> int:
    """
    rough estimate of instruction byte size for pass 1
    exact encoding done by encoder in pass 2

    rules of thumb:
        no operands          ->  1 byte   (NOP, RET, HLT)
        register only        ->  2 bytes  (PUSH, POP, INC, DEC)
        reg + reg            ->  2 bytes  (MOV, ADD, XOR ...)
        reg + imm8           ->  3 bytes
        reg + imm32          ->  6 bytes
        reg + mem            ->  3-7 bytes
        64-bit (REX prefix)  ->  +1 byte
        2-byte opcode (0F)   ->  +1 byte
    """
    mnemonic = instr.mnemonic
    ops      = instr.operands

    # no operands
    if not ops:
        return 1

    # check if any operand is 64-bit
    has_64 = any(
        o.size == OperandSize.QWORD
        for o in ops
        if o.op_type == OperandType.REGISTER
    )
    rex = 1 if has_64 else 0

    # check operand types
    types = [o.op_type for o in ops]

    # jump / call — 2 byte opcode + 4 byte offset
    if mnemonic in (
        "JMP", "CALL",
        "JZ",  "JNZ", "JE",  "JNE",
        "JL",  "JLE", "JG",  "JGE",
        "JB",  "JBE", "JA",  "JAE",
        "JS",  "JNS", "JO",  "JNO",
        "JP",  "JNP", "JCXZ","JECXZ",
        "LOOP","LOOPE","LOOPNE",
    ):
        return 6

    # PUSH / POP reg
    if mnemonic in ("PUSH", "POP") and OperandType.REGISTER in types:
        return 1 + rex

    # SYSCALL — 2 bytes
    if mnemonic == "SYSCALL":
        return 2

    # reg + reg
    if types == [OperandType.REGISTER, OperandType.REGISTER]:
        return 2 + rex

    # reg + imm
    if types == [OperandType.REGISTER, OperandType.IMMEDIATE]:
        imm_size = ops[1].size
        if imm_size == OperandSize.BYTE:
            return 3 + rex
        if imm_size == OperandSize.WORD:
            return 4 + rex
        return 6 + rex      # DWORD / QWORD immediate

    # reg + mem  or  mem + reg
    if OperandType.MEMORY in types:
        op_m = next(o for o in ops if o.op_type == OperandType.MEMORY)
        base = 3 + rex
        if op_m.disp != 0:
            base += 4 if abs(op_m.disp) > 127 else 1
        if op_m.index is not None:
            base += 1       # SIB byte
        return base

    # label ref (JMP/CALL handled above, this catches PUSH label etc.)
    if OperandType.LABEL_REF in types:
        return 5 + rex

    # fallback
    return 4 + rex


def _estimate_data_size(node: IRData) -> int:
    """
    calculate exact byte size of data definition
    DB "hello"  ->  5 bytes
    DD 42       ->  4 bytes
    RESB 64     ->  64 bytes
    """
    size_bytes = {
        OperandSize.BYTE:  1,
        OperandSize.WORD:  2,
        OperandSize.DWORD: 4,
        OperandSize.QWORD: 8,
    }
    unit = size_bytes.get(node.size, 1)

    total = 0
    for v in node.values:
        if isinstance(v, str):
            total += len(v.encode("utf-8"))     # string length
        elif isinstance(v, int):
            total += unit                        # one unit per integer
    return total


# **** Symbol Table ****
class SymbolTable:
    def __init__(self, base_address: int = 0):
        self.base_address = base_address        # ORG value, default 0
        self.symbols: dict[str, Symbol] = {}   # name -> Symbol
        self.globals: set[str]          = set() # names exported globally
        self.externs: set[str]          = set() # names imported externally

    # ── public ────────────────────────────────────────────

    def build(self, program: IRProgram) -> None:
        """
        two pass build:
        pass 1 -> collect all labels, calculate offsets
        pass 2 -> mark globals and externs, resolve references
        """
        self._pass1_collect(program)
        self._pass2_resolve(program)

    def lookup(self, name: str) -> Symbol:
        key = name.upper()
        if key not in self.symbols:
            raise UndefinedLabelError(f"undefined label '{name}'")
        return self.symbols[key]

    def offset_of(self, name: str) -> int:
        return self.lookup(name).offset

    def dump(self):
        print("=" * 50)
        print("  symbol table")
        print("=" * 50)
        for name, sym in sorted(self.symbols.items()):
            flags = []
            if sym.is_global: flags.append("GLOBAL")
            if sym.is_extern: flags.append("EXTERN")
            if sym.is_local:  flags.append("local")
            flag_str = " ".join(flags) if flags else ""
            print(
                f"  {name:<20}"
                f"  0x{sym.offset:08X}"
                f"  {flag_str}"
            )
        print("=" * 50)

    # ── pass 1 : collect labels and calculate offsets ─────

    def _pass1_collect(self, program: IRProgram) -> None:
        """
        walk all nodes in order
        track running byte offset
        when label found -> record its offset
        when instruction found -> add estimated size to offset
        """
        offset = self.base_address

        for node in program.nodes:

            if isinstance(node, IRLabel):
                name = node.name.upper()

                # duplicate label check
                if name in self.symbols and not self.symbols[name].is_extern:
                    raise DuplicateLabelError(
                        f"duplicate label '{node.name}'",
                        line = node.line,
                    )

                sym = Symbol(
                    name     = name,
                    offset   = offset,
                    is_local = node.is_local,
                    line     = node.line,
                )
                self.symbols[name] = sym
                # also store in IRLabel for encoder convenience
                node.offset = offset

            elif isinstance(node, IRInstructions):
                size = _estimate_instruction_size(node)
                offset += size

            elif isinstance(node, IRData):
                size = _estimate_data_size(node)
                offset += size

            elif isinstance(node, IRDirectives):
                # ORG changes the base offset
                if node.name == "ORG" and node.args:
                    offset = node.args[0]
                    self.base_address = offset

    # ****  pass 2 : resolve globals, externs, label refs **** 

    def _pass2_resolve(self, program: IRProgram) -> None:
        """
        walk directives to find GLOBAL and EXTERN declarations
        walk instructions to resolve LABEL_REF operands
        """
        for node in program.nodes:

            # collect GLOBAL declarations
            if isinstance(node, IRDirectives):
                if node.name == "GLOBAL":
                    for arg in node.args:
                        name = str(arg).upper()
                        self.globals.add(name)
                        if name in self.symbols:
                            self.symbols[name].is_global = True

                # collect EXTERN declarations
                elif node.name == "EXTERN":
                    for arg in node.args:
                        name = str(arg).upper()
                        self.externs.add(name)
                        # extern symbols get offset 0 — linker fills them
                        if name not in self.symbols:
                            self.symbols[name] = Symbol(
                                name      = name,
                                offset    = 0,
                                is_extern = True,
                            )

            # resolve label refs in instructions
            elif isinstance(node, IRInstructions):
                for op in node.operands:
                    if op.op_type == OperandType.LABEL_REF:
                        name = str(op.value).upper()
                        if name not in self.symbols and name not in self.externs:
                            raise UndefinedLabelError(
                                f"undefined label '{op.value}'",
                                line = node.line,
                            )
                        if name in self.symbols:
                            # store resolved offset back into operand
                            op.resolved_offset = self.symbols[name].offset
                        else:
                            op.resolved_offset = 0    # extern, linker resolves

        # update global flags on symbols
        for name in self.globals:
            if name in self.symbols:
                self.symbols[name].is_global = True

