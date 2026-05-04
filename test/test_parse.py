# tests/test_parser.py
# testing : Recursive Descent Parser
# runs against lexer + parser + ir together

import pytest
from assembler.lexer import Lexer
from assembler.parser import Parser
from assembler.ir import (
    IRProgram, IRInstructions, IRLabel, IRDirectives, IRData,
    Operand, OperandType, OperandSize,
)


# **** helper ****
def parse(source: str) -> IRProgram:
    tokens  = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    return program


def instrs(source: str) -> list:
    return parse(source).instructions()


def labels(source: str) -> list:
    return parse(source).labels()


def directives(source: str) -> list:
    return parse(source).directives()


def data_nodes(source: str) -> list:
    return parse(source).data()


# ════════════════════════════════════════════════════════════
# 1 — IRProgram structure
# ════════════════════════════════════════════════════════════

class TestIRProgram:

    def test_empty_source_gives_empty_program(self):
        p = parse("")
        assert p.nodes == []

    def test_blank_lines_only_gives_empty_program(self):
        p = parse("\n\n\n")
        assert p.nodes == []

    def test_comment_only_gives_empty_program(self):
        p = parse("; just a comment\n")
        assert p.nodes == []

    def test_program_has_correct_node_count(self):
        source = """
bits 64
_start:
    mov eax, ebx
    nop
"""
        p = parse(source)
        assert len(p.nodes) == 4   # directive + label + 2 instructions

    def test_instructions_filter(self):
        source = """
_start:
    mov eax, ebx
    add eax, 1
"""
        assert len(instrs(source)) == 2

    def test_labels_filter(self):
        source = """
_start:
    mov eax, ebx
loop:
    nop
"""
        assert len(labels(source)) == 2

    def test_directives_filter(self):
        source = """
bits 64
global _start
section .text
"""
        assert len(directives(source)) == 3


# ════════════════════════════════════════════════════════════
# 2 — IRLabel
# ════════════════════════════════════════════════════════════

class TestLabel:

    def test_simple_label(self):
        ls = labels("_start:\n")
        assert len(ls) == 1
        assert ls[0].name == "_start"

    def test_local_label_detected(self):
        ls = labels(".loop:\n")
        assert ls[0].is_local == True

    def test_global_label_not_local(self):
        ls = labels("_start:\n")
        assert ls[0].is_local == False

    def test_multiple_labels(self):
        source = "_start:\nloop:\n.done:\n"
        ls = labels(source)
        assert [l.name for l in ls] == ["_start", "loop", ".done"]

    def test_label_line_number(self):
        source = "\n\n_start:\n"
        ls = labels(source)
        assert ls[0].line == 3

    def test_label_followed_by_instruction(self):
        source = "_start:\n    mov eax, ebx\n"
        p = parse(source)
        assert isinstance(p.nodes[0], IRLabel)
        assert isinstance(p.nodes[1], IRInstructions)


# ════════════════════════════════════════════════════════════
# 3 — IRDirectives
# ════════════════════════════════════════════════════════════

class TestDirectives:

    def test_bits_directive(self):
        ds = directives("bits 64\n")
        assert ds[0].name == "BITS"
        assert ds[0].args == [64]

    def test_bits_32(self):
        ds = directives("bits 32\n")
        assert ds[0].args == [32]

    def test_global_directive(self):
        ds = directives("global _start\n")
        assert ds[0].name == "GLOBAL"
        assert ds[0].args == ["_START"]

    def test_extern_directive(self):
        ds = directives("extern printf\n")
        assert ds[0].name == "EXTERN"
        assert ds[0].args == ["PRINTF"]

    def test_section_directive(self):
        ds = directives("section .text\n")
        assert ds[0].name == "SECTION"

    def test_org_directive(self):
        ds = directives("org 0x1000\n")
        assert ds[0].name == "ORG"
        assert ds[0].args == [0x1000]

    def test_align_directive(self):
        ds = directives("align 16\n")
        assert ds[0].name == "ALIGN"
        assert ds[0].args == [16]

    def test_directive_line_number(self):
        source = "\nbits 64\n"
        ds = directives(source)
        assert ds[0].line == 2


# ════════════════════════════════════════════════════════════
# 4 — IRData
# ════════════════════════════════════════════════════════════

class TestData:

    def test_db_string(self):
        dn = data_nodes('db "hello"\n')
        assert dn[0].size   == OperandSize.BYTE
        assert "hello" in dn[0].values

    def test_db_single_byte(self):
        dn = data_nodes("db 0x41\n")
        assert dn[0].values == [0x41]

    def test_db_multiple_values(self):
        dn = data_nodes('db "hi", 0x0A, 0\n')
        assert "hi"  in dn[0].values
        assert 0x0A  in dn[0].values
        assert 0     in dn[0].values

    def test_dw_size(self):
        dn = data_nodes("dw 1234\n")
        assert dn[0].size == OperandSize.WORD

    def test_dd_size(self):
        dn = data_nodes("dd 0xDEADBEEF\n")
        assert dn[0].size == OperandSize.DWORD

    def test_dq_size(self):
        dn = data_nodes("dq 0\n")
        assert dn[0].size == OperandSize.QWORD

    def test_resb_size(self):
        dn = data_nodes("resb 64\n")
        assert dn[0].size   == OperandSize.BYTE
        assert dn[0].values == [64]

    def test_resw_size(self):
        dn = data_nodes("resw 10\n")
        assert dn[0].size == OperandSize.WORD

    def test_resd_size(self):
        dn = data_nodes("resd 4\n")
        assert dn[0].size == OperandSize.DWORD

    def test_resq_size(self):
        dn = data_nodes("resq 2\n")
        assert dn[0].size == OperandSize.QWORD

    def test_db_negative_value(self):
        dn = data_nodes("db -1\n")
        assert dn[0].values == [-1]

    def test_label_is_none(self):
        # label attached by symbol table pass, not parser
        dn = data_nodes("db 0\n")
        assert dn[0].label is None


# ════════════════════════════════════════════════════════════
# 5 — IRInstructions — mnemonic
# ════════════════════════════════════════════════════════════

class TestInstructionMnemonic:

    def test_nop_no_operands(self):
        ins = instrs("nop\n")
        assert ins[0].mnemonic == "NOP"
        assert ins[0].operands == []

    def test_ret_no_operands(self):
        ins = instrs("ret\n")
        assert ins[0].mnemonic == "RET"
        assert ins[0].operands == []

    def test_hlt_no_operands(self):
        ins = instrs("hlt\n")
        assert ins[0].mnemonic == "HLT"
        assert ins[0].operands == []

    def test_mnemonic_uppercased(self):
        ins = instrs("mov eax, ebx\n")
        assert ins[0].mnemonic == "MOV"

    def test_instruction_line_number(self):
        source = "\n\nmov eax, ebx\n"
        ins = instrs(source)
        assert ins[0].line == 3

    def test_opcode_table_populated(self):
        # IRInstructions should fetch opcodes from OPCODE_TABLE
        ins = instrs("mov eax, ebx\n")
        assert ins[0].opcode != []

    def test_multiple_instructions(self):
        source = "mov eax, ebx\nadd eax, 1\nsub eax, 1\n"
        result = instrs(source)
        assert [i.mnemonic for i in result] == ["MOV", "ADD", "SUB"]


# ════════════════════════════════════════════════════════════
# 6 — Register operands
# ════════════════════════════════════════════════════════════

class TestRegisterOperand:

    def test_32bit_register(self):
        op = instrs("mov eax, ebx\n")[0].operands[0]
        assert op.op_type == OperandType.REGISTER
        assert op.value   == "EAX"
        assert op.size    == OperandSize.DWORD

    def test_64bit_register(self):
        op = instrs("mov rax, rbx\n")[0].operands[0]
        assert op.op_type == OperandType.REGISTER
        assert op.value   == "RAX"
        assert op.size    == OperandSize.QWORD

    def test_8bit_register(self):
        op = instrs("mov al, bl\n")[0].operands[0]
        assert op.op_type == OperandType.REGISTER
        assert op.value   == "AL"
        assert op.size    == OperandSize.BYTE

    def test_16bit_register(self):
        op = instrs("mov ax, bx\n")[0].operands[0]
        assert op.op_type == OperandType.REGISTER
        assert op.size    == OperandSize.WORD

    def test_two_register_operands(self):
        ops = instrs("mov eax, ebx\n")[0].operands
        assert len(ops) == 2
        assert ops[0].value == "EAX"
        assert ops[1].value == "EBX"

    def test_register_name_uppercased(self):
        op = instrs("mov EAX, EBX\n")[0].operands[0]
        assert op.value == "EAX"


# ════════════════════════════════════════════════════════════
# 7 — Immediate operands
# ════════════════════════════════════════════════════════════

class TestImmediateOperand:

    def test_decimal_immediate(self):
        op = instrs("add eax, 42\n")[0].operands[1]
        assert op.op_type == OperandType.IMMEDIATE
        assert op.value   == 42
        assert op.size    == OperandSize.BYTE

    def test_hex_immediate(self):
        op = instrs("add eax, 0xFF\n")[0].operands[1]
        assert op.value == 0xFF
        assert op.size  == OperandSize.BYTE

    def test_binary_immediate(self):
        op = instrs("add eax, 0b1010\n")[0].operands[1]
        assert op.value == 0b1010

    def test_octal_immediate(self):
        op = instrs("add eax, 0o17\n")[0].operands[1]
        assert op.value == 0o17

    def test_negative_immediate(self):
        op = instrs("add eax, -1\n")[0].operands[1]
        assert op.op_type == OperandType.IMMEDIATE
        assert op.value   == -1

    def test_imm_size_byte(self):
        op = instrs("add eax, 1\n")[0].operands[1]
        assert op.size == OperandSize.BYTE

    def test_imm_size_word(self):
        op = instrs("add eax, 1000\n")[0].operands[1]
        assert op.size == OperandSize.WORD

    def test_imm_size_dword(self):
        op = instrs("add eax, 0x10000\n")[0].operands[1]
        assert op.size == OperandSize.DWORD

    def test_large_immediate(self):
        op = instrs("mov rax, 0xDEADBEEF\n")[0].operands[1]
        assert op.value == 0xDEADBEEF


# ════════════════════════════════════════════════════════════
# 8 — Label ref operands
# ════════════════════════════════════════════════════════════

class TestLabelRefOperand:

    def test_jmp_label_ref(self):
        op = instrs("jmp _start\n")[0].operands[0]
        assert op.op_type == OperandType.LABEL_REF
        assert op.value   == "_START"

    def test_call_label_ref(self):
        op = instrs("call printf\n")[0].operands[0]
        assert op.op_type == OperandType.LABEL_REF

    def test_local_label_ref(self):
        op = instrs("jz .done\n")[0].operands[0]
        assert op.op_type == OperandType.LABEL_REF
        assert op.value   == ".DONE"

    def test_label_ref_size_is_none(self):
        op = instrs("jmp _start\n")[0].operands[0]
        assert op.size == OperandSize.NONE


# ════════════════════════════════════════════════════════════
# 9 — Memory operands
# ════════════════════════════════════════════════════════════

class TestMemoryOperand:

    def test_simple_base_register(self):
        op = instrs("mov eax, [ebx]\n")[0].operands[1]
        assert op.op_type == OperandType.MEMORY
        assert op.base    == "EBX"
        assert op.index   is None
        assert op.scale   == 1
        assert op.disp    == 0

    def test_base_plus_displacement(self):
        op = instrs("mov eax, [ebx+8]\n")[0].operands[1]
        assert op.base == "EBX"
        assert op.disp == 8

    def test_base_minus_displacement(self):
        op = instrs("mov eax, [ebx-4]\n")[0].operands[1]
        assert op.base == "EBX"
        assert op.disp == -4

    def test_base_plus_index(self):
        op = instrs("mov eax, [ebx+ecx]\n")[0].operands[1]
        assert op.base  == "EBX"
        assert op.index == "ECX"

    def test_index_with_scale(self):
        op = instrs("mov eax, [ebx+ecx*4]\n")[0].operands[1]
        assert op.base  == "EBX"
        assert op.index == "ECX"
        assert op.scale == 4

    def test_full_sib_expression(self):
        op = instrs("mov eax, [ebx+ecx*4+8]\n")[0].operands[1]
        assert op.base  == "EBX"
        assert op.index == "ECX"
        assert op.scale == 4
        assert op.disp  == 8

    def test_index_scale_only(self):
        op = instrs("mov eax, [ecx*4]\n")[0].operands[1]
        assert op.base  is None
        assert op.index == "ECX"
        assert op.scale == 4

    def test_displacement_only(self):
        op = instrs("mov eax, [0x1000]\n")[0].operands[1]
        assert op.base == None
        assert op.disp == 0x1000

    def test_dword_size_hint(self):
        op = instrs("mov eax, dword [ebx]\n")[0].operands[1]
        assert op.op_type == OperandType.MEMORY
        assert op.size    == OperandSize.DWORD

    def test_qword_size_hint(self):
        op = instrs("mov rax, qword [rbx]\n")[0].operands[1]
        assert op.size == OperandSize.QWORD

    def test_byte_size_hint(self):
        op = instrs("mov al, byte [ebx]\n")[0].operands[1]
        assert op.size == OperandSize.BYTE

    def test_word_size_hint(self):
        op = instrs("mov ax, word [ebx]\n")[0].operands[1]
        assert op.size == OperandSize.WORD

    def test_dword_ptr_syntax(self):
        op = instrs("mov eax, dword ptr [ebx]\n")[0].operands[1]
        assert op.op_type == OperandType.MEMORY
        assert op.size    == OperandSize.DWORD

    def test_rip_relative(self):
        op = instrs("mov rax, [rip+0x10]\n")[0].operands[1]
        assert op.is_rip_relative == True
        assert op.base            == "RIP"

    def test_non_rip_not_relative(self):
        op = instrs("mov eax, [ebx]\n")[0].operands[1]
        assert op.is_rip_relative == False

    def test_memory_type(self):
        op = instrs("mov eax, [ebx]\n")[0].operands[1]
        assert op.op_type == OperandType.MEMORY


# ════════════════════════════════════════════════════════════
# 10 — Mixed operand instructions
# ════════════════════════════════════════════════════════════

class TestMixedOperands:

    def test_reg_mem(self):
        ops = instrs("mov eax, [ebx]\n")[0].operands
        assert ops[0].op_type == OperandType.REGISTER
        assert ops[1].op_type == OperandType.MEMORY

    def test_mem_reg(self):
        ops = instrs("mov [ebx], eax\n")[0].operands
        assert ops[0].op_type == OperandType.MEMORY
        assert ops[1].op_type == OperandType.REGISTER

    def test_reg_imm(self):
        ops = instrs("add eax, 0xFF\n")[0].operands
        assert ops[0].op_type == OperandType.REGISTER
        assert ops[1].op_type == OperandType.IMMEDIATE

    def test_three_operands(self):
        ops = instrs("imul eax, ebx, 4\n")[0].operands
        assert len(ops) == 3

    def test_single_operand(self):
        ops = instrs("push eax\n")[0].operands
        assert len(ops) == 1
        assert ops[0].op_type == OperandType.REGISTER


# ════════════════════════════════════════════════════════════
# 11 — Comments and whitespace
# ════════════════════════════════════════════════════════════

class TestCommentsAndWhitespace:

    def test_inline_comment_ignored(self):
        ins = instrs("mov eax, ebx  ; move ebx into eax\n")
        assert ins[0].mnemonic  == "MOV"
        assert len(ins[0].operands) == 2

    def test_full_line_comment_skipped(self):
        source = "; this is a comment\nmov eax, ebx\n"
        result = instrs(source)
        assert len(result) == 1

    def test_blank_lines_between_instructions(self):
        source = "mov eax, ebx\n\n\nadd eax, 1\n"
        result = instrs(source)
        assert len(result) == 2

    def test_indented_instructions(self):
        source = "    mov eax, ebx\n"
        result = instrs(source)
        assert result[0].mnemonic == "MOV"


# ════════════════════════════════════════════════════════════
# 12 — Full program integration
# ════════════════════════════════════════════════════════════

class TestFullProgram:

    def test_hello_world_structure(self):
        source = """
bits 64
global _start

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
        p = parse(source)
        assert len(p.instructions()) == 8
        assert len(p.labels())       == 2
        assert len(p.directives())   == 2
        assert len(p.data())         == 1

    def test_loop_structure(self):
        source = """
bits 32
    mov ecx, 10
loop:
    dec ecx
    jnz loop
"""
        p = parse(source)
        assert len(p.instructions()) == 3
        assert len(p.labels())       == 1

    def test_enc_pref_default(self):
        ins = instrs("mov eax, ebx\n")
        assert ins[0].enc_pref is not None

    def test_pic_good_default_false(self):
        ins = instrs("mov eax, ebx\n")
        assert ins[0].pic_good == False


# ════════════════════════════════════════════════════════════
# 13 — Error handling
# ════════════════════════════════════════════════════════════

class TestErrors:

    def test_unexpected_token_raises(self):
        with pytest.raises(SyntaxError):
            parse("@ bad token\n")

    def test_unclosed_bracket_raises(self):
        with pytest.raises(SyntaxError):
            parse("mov eax, [ebx\n")

    def test_missing_integer_after_minus_raises(self):
        with pytest.raises((SyntaxError, Exception)):
            parse("add eax, -\n")

    def test_unexpected_operand_raises(self):
        with pytest.raises(SyntaxError):
            parse("mov eax, ]\n")
