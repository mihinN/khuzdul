# test/test_new_opcodes.py
# purpose : verify new opcodes work correctly with
#           lexer, parser, ir layer and symbol_table
# NO encoder involved — just pipeline up to symbol resolution

import pytest
from assembler.lexer         import Lexer
from assembler.parser        import Parser
from assembler.symbol_table  import SymbolTable
from assembler.tokens        import TokensType
from assembler.ir            import (
    IRProgram, IRInstructions, IRLabel, IRDirectives,
    OperandType, OperandSize,
)


# **** helpers ****

def lex(source: str) -> list:
    return Lexer(source).tokenize()


def parse(source: str) -> IRProgram:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


def build(source: str) -> SymbolTable:
    tokens  = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    sym     = SymbolTable()
    sym.build(program)
    return sym


def instrs(source: str) -> list:
    return parse(source).instructions()


def first(source: str) -> IRInstructions:
    return instrs(source)[0]


# ════════════════════════════════════════════════════════════
# 1 — lexer : all new mnemonics classified correctly
# ════════════════════════════════════════════════════════════

class TestLexerNewOpcodes:

    # ── GPA_OPS additions ────────────────────────────────

    def test_adc_is_mnemonic(self):
        t = lex("adc eax, ebx\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "ADC"

    def test_subb_is_mnemonic(self):
        t = lex("subb eax, ebx\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "SUBB"

    def test_test_is_mnemonic(self):
        t = lex("test eax, eax\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "TEST"

    def test_cmp_is_mnemonic(self):
        t = lex("cmp eax, 0\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "CMP"

    def test_xor_is_mnemonic(self):
        t = lex("xor eax, eax\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "XOR"

    def test_sub_is_mnemonic(self):
        t = lex("sub eax, ebx\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "SUB"

    # ── DATA_T additions ─────────────────────────────────

    def test_movsx_is_mnemonic(self):
        t = lex("movsx eax, bx\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "MOVSX"

    def test_movzx_is_mnemonic(self):
        t = lex("movzx eax, bl\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "MOVZX"

    def test_movbe_is_mnemonic(self):
        t = lex("movbe eax, [ebx]\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "MOVBE"

    def test_pushf_is_mnemonic(self):
        t = lex("pushf\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "PUSHF"

    def test_popf_is_mnemonic(self):
        t = lex("popf\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "POPF"

    def test_cmpxchg_is_mnemonic(self):
        t = lex("cmpxchg [ebx], eax\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "CMPXCHG"

    def test_in_is_mnemonic(self):
        t = lex("in al, dx\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "IN"

    def test_out_is_mnemonic(self):
        t = lex("out dx, al\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "OUT"

    # ── BIT_MANI additions ───────────────────────────────

    def test_bt_is_mnemonic(self):
        t = lex("bt eax, 1\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "BT"

    def test_btc_is_mnemonic(self):
        t = lex("btc eax, 1\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "BTC"

    def test_btr_is_mnemonic(self):
        t = lex("btr eax, 1\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "BTR"

    def test_bts_is_mnemonic(self):
        t = lex("bts eax, 1\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "BTS"

    def test_bsr_is_mnemonic(self):
        t = lex("bsr eax, ebx\n")
        assert t[0].type  == TokensType.MNEMONIC
        assert t[0].value == "BSR"

    # ── operands still tokenize correctly ────────────────

    def test_new_opcode_register_operands(self):
        t = lex("adc eax, ebx\n")
        assert t[1].type  == TokensType.REGISTER
        assert t[1].value == "EAX"
        assert t[3].type  == TokensType.REGISTER
        assert t[3].value == "EBX"

    def test_new_opcode_immediate_operand(self):
        t = lex("cmp eax, 0xFF\n")
        assert t[3].type  == TokensType.INTEGER
        assert t[3].value == "0xFF"

    def test_new_opcode_memory_operand(self):
        t = lex("cmpxchg [ebx], eax\n")
        assert t[1].type == TokensType.LBRACKET
        assert t[2].type == TokensType.REGISTER


# ════════════════════════════════════════════════════════════
# 2 — parser : new opcodes build correct IR nodes
# ════════════════════════════════════════════════════════════

class TestParserNewOpcodes:

    # ── GPA_OPS ──────────────────────────────────────────

    def test_adc_two_registers(self):
        i = first("adc eax, ebx\n")
        assert i.mnemonic                  == "ADC"
        assert len(i.operands)             == 2
        assert i.operands[0].op_type       == OperandType.REGISTER
        assert i.operands[0].value         == "EAX"
        assert i.operands[1].op_type       == OperandType.REGISTER
        assert i.operands[1].value         == "EBX"

    def test_adc_reg_imm(self):
        i = first("adc eax, 1\n")
        assert i.mnemonic                  == "ADC"
        assert i.operands[1].op_type       == OperandType.IMMEDIATE
        assert i.operands[1].value         == 1

    def test_sub_reg_reg(self):
        i = first("sub eax, ebx\n")
        assert i.mnemonic                  == "SUB"
        assert i.operands[0].value         == "EAX"
        assert i.operands[1].value         == "EBX"

    def test_sub_reg_imm(self):
        i = first("sub rax, 0xFF\n")
        assert i.mnemonic                  == "SUB"
        assert i.operands[1].value         == 0xFF

    def test_xor_reg_reg(self):
        i = first("xor eax, eax\n")
        assert i.mnemonic                  == "XOR"
        assert i.operands[0].value         == "EAX"
        assert i.operands[1].value         == "EAX"

    def test_xor_rdi_rdi(self):
        i = first("xor rdi, rdi\n")
        assert i.mnemonic                  == "XOR"
        assert i.operands[0].size          == OperandSize.QWORD
        assert i.operands[1].size          == OperandSize.QWORD

    def test_cmp_reg_reg(self):
        i = first("cmp eax, ebx\n")
        assert i.mnemonic                  == "CMP"
        assert len(i.operands)             == 2

    def test_cmp_reg_imm(self):
        i = first("cmp eax, 0\n")
        assert i.mnemonic                  == "CMP"
        assert i.operands[1].op_type       == OperandType.IMMEDIATE
        assert i.operands[1].value         == 0

    def test_cmp_reg_mem(self):
        i = first("cmp eax, [ebx]\n")
        assert i.mnemonic                  == "CMP"
        assert i.operands[1].op_type       == OperandType.MEMORY
        assert i.operands[1].base          == "EBX"

    def test_test_reg_reg(self):
        i = first("test eax, eax\n")
        assert i.mnemonic                  == "TEST"
        assert len(i.operands)             == 2

    def test_test_reg_imm(self):
        i = first("test eax, 0xFF\n")
        assert i.mnemonic                  == "TEST"
        assert i.operands[1].value         == 0xFF

    # ── DATA_T ───────────────────────────────────────────

    def test_movsx_reg_reg(self):
        i = first("movsx eax, bx\n")
        assert i.mnemonic                  == "MOVSX"
        assert i.operands[0].value         == "EAX"
        assert i.operands[1].value         == "BX"

    def test_movzx_reg_reg(self):
        i = first("movzx eax, bl\n")
        assert i.mnemonic                  == "MOVZX"
        assert i.operands[0].value         == "EAX"
        assert i.operands[1].value         == "BL"

    def test_movbe_reg_mem(self):
        i = first("movbe eax, [ebx]\n")
        assert i.mnemonic                  == "MOVBE"
        assert i.operands[0].op_type       == OperandType.REGISTER
        assert i.operands[1].op_type       == OperandType.MEMORY

    def test_pushf_no_operands(self):
        i = first("pushf\n")
        assert i.mnemonic                  == "PUSHF"
        assert len(i.operands)             == 0

    def test_popf_no_operands(self):
        i = first("popf\n")
        assert i.mnemonic                  == "POPF"
        assert len(i.operands)             == 0

    def test_cmpxchg_mem_reg(self):
        i = first("cmpxchg [ebx], eax\n")
        assert i.mnemonic                  == "CMPXCHG"
        assert i.operands[0].op_type       == OperandType.MEMORY
        assert i.operands[0].base          == "EBX"
        assert i.operands[1].op_type       == OperandType.REGISTER
        assert i.operands[1].value         == "EAX"

    def test_in_reg_reg(self):
        i = first("in al, dx\n")
        assert i.mnemonic                  == "IN"
        assert i.operands[0].value         == "AL"
        assert i.operands[1].value         == "DX"

    def test_out_reg_reg(self):
        i = first("out dx, al\n")
        assert i.mnemonic                  == "OUT"
        assert i.operands[0].value         == "DX"
        assert i.operands[1].value         == "AL"

    # ── BIT_MANI ─────────────────────────────────────────

    def test_bt_reg_imm(self):
        i = first("bt eax, 1\n")
        assert i.mnemonic                  == "BT"
        assert i.operands[0].op_type       == OperandType.REGISTER
        assert i.operands[1].op_type       == OperandType.IMMEDIATE
        assert i.operands[1].value         == 1

    def test_bt_reg_reg(self):
        i = first("bt eax, ecx\n")
        assert i.mnemonic                  == "BT"
        assert i.operands[1].op_type       == OperandType.REGISTER

    def test_btc_reg_imm(self):
        i = first("btc eax, 3\n")
        assert i.mnemonic                  == "BTC"
        assert i.operands[1].value         == 3

    def test_btr_reg_imm(self):
        i = first("btr eax, 0\n")
        assert i.mnemonic                  == "BTR"
        assert i.operands[1].value         == 0

    def test_bts_reg_imm(self):
        i = first("bts eax, 7\n")
        assert i.mnemonic                  == "BTS"
        assert i.operands[1].value         == 7

    def test_bsr_reg_reg(self):
        i = first("bsr eax, ebx\n")
        assert i.mnemonic                  == "BSR"
        assert i.operands[0].value         == "EAX"
        assert i.operands[1].value         == "EBX"

    # ── operand sizes correct ────────────────────────────

    def test_32bit_operand_size(self):
        i = first("cmp eax, ebx\n")
        assert i.operands[0].size == OperandSize.DWORD
        assert i.operands[1].size == OperandSize.DWORD

    def test_64bit_operand_size(self):
        i = first("xor rax, rax\n")
        assert i.operands[0].size == OperandSize.QWORD
        assert i.operands[1].size == OperandSize.QWORD

    def test_8bit_operand_size(self):
        i = first("in al, dx\n")
        assert i.operands[0].size == OperandSize.BYTE


# ════════════════════════════════════════════════════════════
# 3 — IR layer : opcode table populated correctly
# ════════════════════════════════════════════════════════════

class TestIROpcodeTable:

    def test_adc_opcode_populated(self):
        i = first("adc eax, ebx\n")
        assert i.opcode != []
        assert b"\x11" in i.opcode     # ADC r/m32, r32

    def test_sub_opcode_populated(self):
        i = first("sub eax, ebx\n")
        assert i.opcode != []
        assert b"\x29" in i.opcode     # SUB r/m32, r32

    def test_xor_opcode_populated(self):
        i = first("xor eax, eax\n")
        assert i.opcode != []
        assert b"\x31" in i.opcode     # XOR r/m32, r32

    def test_cmp_opcode_populated(self):
        i = first("cmp eax, ebx\n")
        assert i.opcode != []
        assert b"\x39" in i.opcode     # CMP r/m32, r32

    def test_test_opcode_populated(self):
        i = first("test eax, eax\n")
        assert i.opcode != []
        assert b"\x85" in i.opcode     # TEST r/m32, r32

    def test_movsx_opcode_populated(self):
        i = first("movsx eax, bx\n")
        assert i.opcode != []
        assert b"\x0F\xBF" in i.opcode  # MOVSX r32, r/m16

    def test_movzx_opcode_populated(self):
        i = first("movzx eax, bl\n")
        assert i.opcode != []
        assert b"\x0F\xB6" in i.opcode  # MOVZX r32, r/m8

    def test_bt_opcode_populated(self):
        i = first("bt eax, ecx\n")
        assert i.opcode != []
        assert b"\x0F\xA3" in i.opcode  # BT r/m32, r32

    def test_cmpxchg_opcode_populated(self):
        i = first("cmpxchg [ebx], eax\n")
        assert i.opcode != []
        assert b"\x0F\xB1" in i.opcode  # CMPXCHG r/m32, r32

    def test_unknown_mnemonic_empty_opcode(self):
        # unknown mnemonics get empty opcode list
        i = first("fakeinstr eax\n")
        assert i.opcode == []

    def test_enc_pref_default(self):
        i = first("cmp eax, ebx\n")
        assert i.enc_pref is not None

    def test_pic_good_default_false(self):
        i = first("xor rax, rax\n")
        assert i.pic_good == False


# ════════════════════════════════════════════════════════════
# 4 — symbol table : new opcodes work with labels
# ════════════════════════════════════════════════════════════

class TestSymbolTableNewOpcodes:

    def test_cmp_then_jne(self):
        source = """
_start:
    cmp  eax, 0
    jne  end
end:
    ret
"""
        sym = build(source)
        assert "_START" in sym.symbols
        assert "END"    in sym.symbols
        assert sym.symbols["END"].offset > sym.symbols["_START"].offset

    def test_test_then_jz(self):
        source = """
_start:
    test eax, eax
    jz   zero
zero:
    ret
"""
        sym = build(source)
        assert "ZERO" in sym.symbols
        assert sym.symbols["ZERO"].offset > 0

    def test_xor_advances_offset(self):
        source = """
_start:
    xor eax, eax
end:
"""
        sym = build(source)
        # xor eax, eax = reg+reg = 2 bytes
        assert sym.symbols["END"].offset == 2

    def test_sub_advances_offset(self):
        source = """
_start:
    sub eax, ebx
end:
"""
        sym = build(source)
        # sub eax, ebx = reg+reg = 2 bytes
        assert sym.symbols["END"].offset == 2

    def test_cmp_advances_offset(self):
        source = """
_start:
    cmp eax, 1
end:
"""
        sym = build(source)
        # cmp eax, imm8 = 3 bytes
        assert sym.symbols["END"].offset == 3

    def test_label_ref_in_jne_resolved(self):
        source = """
_start:
    cmp  eax, 0
    jne  done
done:
    ret
"""
        tokens  = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        sym     = SymbolTable()
        sym.build(program)

        # find jne instruction
        jne = None
        for instr in program.instructions():
            if instr.mnemonic == "JNE":
                jne = instr
                break

        assert jne is not None
        op = jne.operands[0]
        assert op.op_type         == OperandType.LABEL_REF
        assert op.resolved_offset == sym.symbols["DONE"].offset

    def test_loop_with_cmp(self):
        source = """
bits 64
_start:
    mov  ecx, 10
loop:
    dec  ecx
    cmp  ecx, 0
    jnz  loop
    ret
"""
        sym = build(source)
        assert "_START" in sym.symbols
        assert "LOOP"   in sym.symbols
        assert sym.symbols["LOOP"].offset > 0

    def test_adc_advances_offset(self):
        source = """
_start:
    adc eax, ebx
end:
"""
        sym = build(source)
        # adc eax, ebx = reg+reg = 2 bytes
        assert sym.symbols["END"].offset == 2


# ════════════════════════════════════════════════════════════
# 5 — memory operands with new opcodes
# ════════════════════════════════════════════════════════════

class TestMemoryOperandsNewOpcodes:

    def test_cmp_reg_mem_base(self):
        i = first("cmp eax, [ebx]\n")
        assert i.operands[1].op_type == OperandType.MEMORY
        assert i.operands[1].base    == "EBX"
        assert i.operands[1].disp    == 0

    def test_cmp_reg_mem_disp(self):
        i = first("cmp eax, [ebx+8]\n")
        assert i.operands[1].base    == "EBX"
        assert i.operands[1].disp    == 8

    def test_test_mem_reg(self):
        i = first("test [ebx], eax\n")
        assert i.operands[0].op_type == OperandType.MEMORY
        assert i.operands[1].op_type == OperandType.REGISTER

    def test_bt_mem_reg(self):
        i = first("bt [eax], ecx\n")
        assert i.operands[0].op_type == OperandType.MEMORY
        assert i.operands[0].base    == "EAX"

    def test_cmpxchg_mem_sib(self):
        i = first("cmpxchg [ebx+ecx*4], eax\n")
        assert i.operands[0].op_type == OperandType.MEMORY
        assert i.operands[0].base    == "EBX"
        assert i.operands[0].index   == "ECX"
        assert i.operands[0].scale   == 4

    def test_movbe_mem_reg(self):
        i = first("movbe [ebx], eax\n")
        assert i.operands[0].op_type == OperandType.MEMORY
        assert i.operands[1].op_type == OperandType.REGISTER

    def test_size_hint_with_new_opcode(self):
        i = first("cmp eax, dword [ebx]\n")
        assert i.operands[1].size    == OperandSize.DWORD
        assert i.operands[1].op_type == OperandType.MEMORY


# ════════════════════════════════════════════════════════════
# 6 — full program with new opcodes end to end
# ════════════════════════════════════════════════════════════

class TestFullProgramNewOpcodes:

    def test_compare_and_branch(self):
        source = """
bits 64
global _start

_start:
    xor  rax, rax
    xor  rbx, rbx
    cmp  rax, rbx
    jne  not_equal
    ret
not_equal:
    mov  rax, 1
    ret
"""
        program = parse(source)
        sym     = SymbolTable()
        sym.build(program)

        assert len(program.instructions()) == 6
        assert "NOT_EQUAL" in sym.symbols
        assert sym.symbols["NOT_EQUAL"].offset > 0

    def test_bit_test_program(self):
        source = """
bits 64
_start:
    mov  eax, 0xFF
    bt   eax, 3
    jc   bit_set
    ret
bit_set:
    xor  eax, eax
    ret
"""
        program = parse(source)
        sym     = SymbolTable()
        sym.build(program)

        assert "BIT_SET" in sym.symbols
        mnemonics = [i.mnemonic for i in program.instructions()]
        assert "MOV"  in mnemonics
        assert "BT"   in mnemonics
        assert "XOR"  in mnemonics

    def test_adc_program(self):
        source = """
bits 64
_start:
    xor  rax, rax
    xor  rbx, rbx
    add  eax, 0xFF
    adc  ebx, 0
    ret
"""
        program = parse(source)
        mnemonics = [i.mnemonic for i in program.instructions()]
        assert "ADC" in mnemonics
        assert "ADD" in mnemonics
        assert "XOR" in mnemonics

    def test_cmpxchg_program(self):
        source = """
bits 64
_start:
    mov  eax, 0
    cmpxchg [rsp], ebx
    ret
"""
        program = parse(source)
        i = program.instructions()[1]
        assert i.mnemonic          == "CMPXCHG"
        assert i.operands[0].op_type == OperandType.MEMORY

    def test_test_and_jz(self):
        source = """
bits 64
_start:
    test rax, rax
    jz   is_zero
    ret
is_zero:
    xor  rax, rax
    ret
"""
        program = parse(source)
        sym     = SymbolTable()
        sym.build(program)

        assert "IS_ZERO" in sym.symbols

        jz = next(i for i in program.instructions() if i.mnemonic == "JZ")
        assert jz.operands[0].resolved_offset == sym.symbols["IS_ZERO"].offset
