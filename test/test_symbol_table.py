# test/test_symbol_table.py
# testing : SymbolTable — two pass symbol resolution
# covers : pass1 offset calculation, pass2 resolution,
#          globals, externs, errors, PIC, ORG directive

import pytest
from assembler.lexer         import Lexer
from assembler.parser        import Parser
from assembler.symbol_table  import (
    SymbolTable,
    Symbol,
    SymbolError,
    DuplicateLabelError,
    UndefinedLabelError,
)
from assembler.ir import (
    IRProgram, IRInstructions, IRLabel, IRDirectives, IRData,
    Operand, OperandType, OperandSize,
)


# **** helpers ****

def build(source: str, base: int = 0) -> SymbolTable:
    tokens  = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    sym     = SymbolTable(base_address=base)
    sym.build(program)
    return sym


def program_of(source: str) -> IRProgram:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


# ════════════════════════════════════════════════════════════
# 1 — Symbol class
# ════════════════════════════════════════════════════════════

class TestSymbol:

    def test_symbol_default_values(self):
        s = Symbol(name="TEST")
        assert s.name      == "TEST"
        assert s.offset    == 0
        assert s.is_global == False
        assert s.is_extern == False
        assert s.is_local  == False
        assert s.line      == 0

    def test_symbol_with_values(self):
        s = Symbol(
            name      = "_START",
            offset    = 0x10,
            is_global = True,
            is_extern = False,
            is_local  = False,
            line      = 5,
        )
        assert s.offset    == 0x10
        assert s.is_global == True
        assert s.line      == 5

    def test_symbol_repr(self):
        s = Symbol(name="LOOP", offset=0x20)
        r = repr(s)
        assert "LOOP"   in r
        assert "0x0020" in r

    def test_local_symbol(self):
        s = Symbol(name=".loop", is_local=True)
        assert s.is_local == True

    def test_extern_symbol(self):
        s = Symbol(name="PRINTF", is_extern=True)
        assert s.is_extern == True


# ════════════════════════════════════════════════════════════
# 2 — SymbolTable init
# ════════════════════════════════════════════════════════════

class TestSymbolTableInit:

    def test_default_base_address(self):
        sym = SymbolTable()
        assert sym.base_address == 0

    def test_custom_base_address(self):
        sym = SymbolTable(base_address=0x1000)
        assert sym.base_address == 0x1000

    def test_empty_symbols_on_init(self):
        sym = SymbolTable()
        assert sym.symbols == {}
        assert sym.globals  == set()
        assert sym.externs  == set()

    def test_empty_source_builds_empty_table(self):
        sym = build("")
        assert sym.symbols == {}

    def test_comment_only_builds_empty_table(self):
        sym = build("; just a comment\n")
        assert sym.symbols == {}


# ════════════════════════════════════════════════════════════
# 3 — Pass 1 : label collection
# ════════════════════════════════════════════════════════════

class TestPass1LabelCollection:

    def test_single_label_at_zero(self):
        sym = build("_start:\n    nop\n")
        assert "_START" in sym.symbols
        assert sym.symbols["_START"].offset == 0

    def test_label_after_instruction(self):
        # nop = 1 byte, so loop should be at offset 1
        sym = build("_start:\n    nop\nloop:\n")
        assert sym.symbols["LOOP"].offset == 1

    def test_multiple_labels(self):
        source = """
_start:
    nop
loop:
    nop
    nop
done:
"""
        sym = build(source)
        assert "_START" in sym.symbols
        assert "LOOP"   in sym.symbols
        assert "DONE"   in sym.symbols

    def test_label_offsets_increase(self):
        source = """
_start:
    nop
loop:
    nop
done:
"""
        sym = build(source)
        assert sym.symbols["_START"].offset < sym.symbols["LOOP"].offset
        assert sym.symbols["LOOP"].offset   < sym.symbols["DONE"].offset

    def test_local_label_collected(self):
        sym = build(".loop:\n    nop\n")
        assert ".LOOP" in sym.symbols

    def test_local_label_is_local_flag(self):
        sym = build(".loop:\n    nop\n")
        assert sym.symbols[".LOOP"].is_local == True

    def test_global_label_not_local(self):
        sym = build("_start:\n    nop\n")
        assert sym.symbols["_START"].is_local == False

    def test_label_name_uppercased(self):
        sym = build("myLabel:\n    nop\n")
        assert "MYLABEL" in sym.symbols

    def test_data_advances_offset(self):
        # db "hello" = 5 bytes
        # so loop should be at offset 5
        source = """
msg:
    db "hello"
loop:
    nop
"""
        sym = build(source)
        assert sym.symbols["LOOP"].offset == 5

    def test_irLabel_offset_set(self):
        # IRLabel.offset should be set during pass1
        source  = "_start:\n    nop\n"
        tokens  = Lexer(source).tokenize()
        prog    = Parser(tokens).parse()
        sym     = SymbolTable()
        sym.build(prog)
        label = prog.labels()[0]
        assert label.offset == 0


# ════════════════════════════════════════════════════════════
# 4 — Pass 1 : instruction size estimation
# ════════════════════════════════════════════════════════════

class TestInstructionSizeEstimation:

    def test_nop_is_1_byte(self):
        source = "_start:\n    nop\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 1

    def test_ret_is_1_byte(self):
        source = "_start:\n    ret\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 1

    def test_syscall_is_2_bytes(self):
        # fix 1: SYSCALL = 0F 05 = 2 bytes
        source = "_start:\n    syscall\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 2
    def test_jmp_label_is_5_bytes(self):
        source = "_start:\n    jmp loop\nend:\nloop:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 5

    def test_call_is_5_bytes(self):
        source = "_start:\n    call func\nend:\nfunc:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 5
    def test_jmp_label_is_6_bytes(self):
        source = "_start:\n    jmp loop\nend:\nloop:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 6

    def test_call_is_6_bytes(self):
        source = "_start:\n    call func\nend:\nfunc:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 6

    def test_reg_reg_is_2_bytes(self):
        source = "_start:\n    mov eax, ebx\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 2

    def test_64bit_reg_adds_rex(self):
        # 64-bit reg gets REX prefix → 3 bytes
        source = "_start:\n    mov rax, rbx\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 3

    def test_reg_imm8_is_3_bytes(self):
        source = "_start:\n    add eax, 1\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 3

    def test_push_reg_is_1_byte(self):
        source = "_start:\n    push eax\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 1

    def test_pop_reg_is_1_byte(self):
        source = "_start:\n    pop ebx\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 1


# ════════════════════════════════════════════════════════════
# 5 — Pass 1 : data size calculation
# ════════════════════════════════════════════════════════════

class TestDataSizeCalculation:

    def test_db_string_size(self):
        # "hello" = 5 bytes
        source = 'msg:\n    db "hello"\nend:\n'
        sym = build(source)
        assert sym.symbols["END"].offset == 5

    def test_db_single_byte(self):
        source = "msg:\n    db 0x41\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 1

    def test_db_multiple_bytes(self):
        source = "msg:\n    db 0x41, 0x42, 0x43\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 3

    def test_dw_is_2_bytes(self):
        source = "num:\n    dw 1234\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 2

    def test_dd_is_4_bytes(self):
        source = "num:\n    dd 0xDEADBEEF\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 4

    def test_dq_is_8_bytes(self):
        source = "num:\n    dq 0\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 8

    def test_resb_size(self):
        # fix 2: resb 10 = 10 * 1 = 10 bytes
        source = "buf:\n    resb 10\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 10

    def test_resw_size(self):
        # fix 2: resw 4 = 4 * 2 = 8 bytes
        source = "buf:\n    resw 4\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 8

    def test_resd_size(self):
        # fix 2: resd 2 = 2 * 4 = 8 bytes
        source = "buf:\n    resd 2\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 8

    def test_resq_size(self):
        # fix 2: resq 1 = 1 * 8 = 8 bytes
        source = "buf:\n    resq 1\nend:\n"
        sym = build(source)
        assert sym.symbols["END"].offset == 8

    def test_string_with_null(self):
        # "hi" + 0x00 = 3 bytes
        source = 'msg:\n    db "hi", 0x00\nend:\n'
        sym = build(source)
        assert sym.symbols["END"].offset == 3


# ════════════════════════════════════════════════════════════
# 6 — ORG directive
# ════════════════════════════════════════════════════════════

class TestOrgDirective:

    def test_org_sets_base(self):
        source = "org 0x1000\n_start:\n    nop\n"
        sym = build(source)
        assert sym.symbols["_START"].offset == 0x1000

    def test_org_changes_subsequent_offsets(self):
        source = """
org 0x1000
_start:
    nop
loop:
"""
        sym = build(source)
        assert sym.symbols["_START"].offset == 0x1000
        assert sym.symbols["LOOP"].offset   == 0x1001

    def test_org_updates_base_address(self):
        source = "org 0x2000\n_start:\n"
        sym = build(source)
        assert sym.base_address == 0x2000

    def test_custom_base_address(self):
        sym = build("_start:\n    nop\n", base=0x400000)
        assert sym.symbols["_START"].offset == 0x400000


# ════════════════════════════════════════════════════════════
# 7 — Pass 2 : GLOBAL and EXTERN
# ════════════════════════════════════════════════════════════

class TestGlobalAndExtern:

    def test_global_marks_symbol(self):
        source = """
global _start
_start:
    nop
"""
        sym = build(source)
        assert sym.symbols["_START"].is_global == True

    def test_global_added_to_globals_set(self):
        source = "global _start\n_start:\n    nop\n"
        sym = build(source)
        assert "_START" in sym.globals

    def test_extern_adds_to_externs_set(self):
        source = "extern printf\n    call printf\n"
        sym = build(source)
        assert "PRINTF" in sym.externs

    def test_extern_symbol_offset_is_zero(self):
        source = "extern printf\n    call printf\n"
        sym = build(source)
        assert sym.symbols["PRINTF"].offset == 0

    def test_extern_symbol_is_extern_flag(self):
        source = "extern printf\n    call printf\n"
        sym = build(source)
        assert sym.symbols["PRINTF"].is_extern == True

    def test_multiple_globals(self):
        source = """
global _start
global _end
_start:
    nop
_end:
    ret
"""
        sym = build(source)
        assert sym.symbols["_START"].is_global == True
        assert sym.symbols["_END"].is_global   == True

    def test_multiple_externs(self):
        source = """
extern printf
extern malloc
extern free
    call printf
    call malloc
    call free
"""
        sym = build(source)
        assert "PRINTF" in sym.externs
        assert "MALLOC" in sym.externs
        assert "FREE"   in sym.externs

    def test_non_global_label_not_marked(self):
        source = """
global _start
_start:
    nop
loop:
    nop
"""
        sym = build(source)
        assert sym.symbols["_START"].is_global == True
        assert sym.symbols["LOOP"].is_global   == False


# ════════════════════════════════════════════════════════════
# 8 — Pass 2 : label reference resolution
# ════════════════════════════════════════════════════════════

class TestLabelRefResolution:

    def test_jmp_label_ref_resolved(self):
        source = """
_start:
    nop
    jmp loop
loop:
    nop
"""
        tokens  = Lexer(source).tokenize()
        prog    = Parser(tokens).parse()
        sym     = SymbolTable()
        sym.build(prog)

        jmp_instr = None
        for instr in prog.instructions():
            if instr.mnemonic == "JMP":
                jmp_instr = instr
                break

        assert jmp_instr is not None
        op = jmp_instr.operands[0]
        assert op.op_type         == OperandType.LABEL_REF
        assert hasattr(op, "resolved_offset")
        assert op.resolved_offset == sym.symbols["LOOP"].offset

    def test_call_label_ref_resolved(self):
        source = """
_start:
    call func
func:
    ret
"""
        tokens  = Lexer(source).tokenize()
        prog    = Parser(tokens).parse()
        sym     = SymbolTable()
        sym.build(prog)

        call_instr = prog.instructions()[0]
        op = call_instr.operands[0]
        assert op.resolved_offset == sym.symbols["FUNC"].offset

    def test_forward_reference_resolved(self):
        # label used before defined
        source = """
    jmp end
    nop
end:
    ret
"""
        tokens  = Lexer(source).tokenize()
        prog    = Parser(tokens).parse()
        sym     = SymbolTable()
        sym.build(prog)

        jmp_instr = prog.instructions()[0]
        op = jmp_instr.operands[0]
        assert op.resolved_offset == sym.symbols["END"].offset

    def test_extern_ref_resolved_to_zero(self):
        source = """
extern printf
    call printf
"""
        tokens  = Lexer(source).tokenize()
        prog    = Parser(tokens).parse()
        sym     = SymbolTable()
        sym.build(prog)

        call_instr = prog.instructions()[0]
        op = call_instr.operands[0]
        assert op.resolved_offset == 0    # linker fills this


# ════════════════════════════════════════════════════════════
# 9 — lookup and offset_of
# ════════════════════════════════════════════════════════════

class TestLookup:

    def test_lookup_existing_symbol(self):
        sym = build("_start:\n    nop\n")
        s   = sym.lookup("_start")
        assert s.name == "_START"

    def test_lookup_case_insensitive(self):
        sym = build("_start:\n    nop\n")
        assert sym.lookup("_start").offset == sym.lookup("_START").offset

    def test_lookup_undefined_raises(self):
        sym = build("_start:\n    nop\n")
        with pytest.raises(UndefinedLabelError):
            sym.lookup("nonexistent")

    def test_offset_of_existing(self):
        sym = build("_start:\n    nop\nloop:\n")
        assert sym.offset_of("loop") == 1

    def test_offset_of_undefined_raises(self):
        sym = build("_start:\n    nop\n")
        with pytest.raises(UndefinedLabelError):
            sym.offset_of("missing")


# ════════════════════════════════════════════════════════════
# 10 — Error handling
# ════════════════════════════════════════════════════════════

class TestErrors:

    def test_duplicate_label_raises(self):
        source = """
_start:
    nop
_start:
    ret
"""
        with pytest.raises(DuplicateLabelError):
            build(source)

    def test_duplicate_local_label_raises(self):
        source = """
.loop:
    nop
.loop:
    ret
"""
        with pytest.raises(DuplicateLabelError):
            build(source)

    def test_undefined_label_ref_raises(self):
        source = "    jmp nonexistent\n"
        with pytest.raises(UndefinedLabelError):
            build(source)

    def test_symbol_error_has_line(self):
        try:
            build("    jmp nonexistent\n")
        except UndefinedLabelError as e:
            assert e.line >= 0

    def test_duplicate_error_message(self):
        source = "_start:\n    nop\n_start:\n    ret\n"
        with pytest.raises(DuplicateLabelError, match="(?i)_start"):   # fix: case insensitive
            build(source)

    def test_undefined_error_message(self):
        source = "    jmp missing\n"
        with pytest.raises(UndefinedLabelError, match="(?i)missing"):  # fix: case insensitive
            build(source)


# ════════════════════════════════════════════════════════════
# 11 — Full program integration
# ════════════════════════════════════════════════════════════

class TestFullProgram:

    def test_hello_world_symbols(self):
        source = """
bits 64
global _start
extern write
extern exit

_start:
    mov  rax, 1
    mov  rdi, 1
    mov  rsi, msg
    mov  rdx, 13
    syscall
    mov  rax, 60
    xor  rdi, rdi
    syscall

msg:
    db "hello world", 0x0A
"""
        sym = build(source)
        assert "_START" in sym.symbols
        assert "MSG"    in sym.symbols
        assert "WRITE"  in sym.externs
        assert "EXIT"   in sym.externs
        assert sym.symbols["_START"].is_global == True
        assert sym.symbols["MSG"].offset > sym.symbols["_START"].offset

    def test_loop_program_symbols(self):
        source = """
bits 32
    mov ecx, 10
loop:
    dec ecx
    jnz loop
    ret
"""
        sym = build(source)
        assert "LOOP" in sym.symbols
        assert sym.symbols["LOOP"].offset > 0

    def test_symbol_table_dump(self, capsys):
        source = "global _start\n_start:\n    nop\n"
        sym = build(source)
        sym.dump()
        captured = capsys.readouterr()
        assert "_START" in captured.out
        assert "GLOBAL" in captured.out

    def test_org_with_full_program(self):
        source = """
org 0x7C00
_start:
    nop
    nop
end:
    ret
"""
        sym = build(source)
        assert sym.symbols["_START"].offset == 0x7C00
        assert sym.symbols["END"].offset    == 0x7C02

    def test_mixed_data_and_code(self):
        source = """
_start:
    mov eax, 1
    nop
data:
    db 0x41, 0x42
end:
"""
        sym = build(source)
        assert sym.symbols["_START"].offset == 0
        assert sym.symbols["DATA"].offset   >  0
        assert sym.symbols["END"].offset    == sym.symbols["DATA"].offset + 2