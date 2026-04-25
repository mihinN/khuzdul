import pytest
from assembler.lexer import Lexer
from assembler.tokens import TokensType


def lex(source: str):
    """Helper — returns token list without EOF."""
    tokens = Lexer(source).tokenize()
    return [t for t in tokens if t.type != TokensType.EOF]


def types(source: str):
    """Helper — returns just the token types."""
    return [t.type for t in lex(source)]


def values(source: str):
    """Helper — returns just the token values."""
    return [t.value for t in lex(source)]


# ── comments ─────────────────────────────────────────────────────

def test_comment_basic():
    toks = lex("; this is a comment")
    assert len(toks) == 1
    assert toks[0].type  == TokensType.COMMENTS
    assert toks[0].value == "; this is a comment"

def test_comment_does_not_eat_newline():
    toks = lex("; comment\n")
    assert toks[0].type == TokensType.COMMENTS
    assert toks[1].type == TokensType.NEWLINE

def test_comment_after_instruction():
    toks = lex("MOV EAX, 1 ; load 1")
    assert toks[-1].type == TokensType.COMMENTS


# ── newline ───────────────────────────────────────────────────────

def test_newline_token():
    toks = lex("\n")
    assert toks[0].type  == TokensType.NEWLINE
    assert toks[0].value == "\n"

def test_newline_increments_line():
    tokens = Lexer("MOV\nADD").tokenize()
    add_tok = [t for t in tokens if t.value == "ADD"][0]
    assert add_tok.line == 2

def test_multiple_newlines():
    toks = lex("\n\n\n")
    assert all(t.type == TokensType.NEWLINE for t in toks)
    assert len(toks) == 3


# ── strings ───────────────────────────────────────────────────────

def test_string_basic():
    toks = lex('"hello"')
    assert toks[0].type  == TokensType.STRING
    assert toks[0].value == "hello"

def test_string_empty():
    toks = lex('""')
    assert toks[0].type  == TokensType.STRING
    assert toks[0].value == ""

def test_string_unterminated():
    with pytest.raises(SyntaxError):
        Lexer('"unterminated').tokenize()

def test_string_with_spaces():
    toks = lex('"hello world"')
    assert toks[0].value == "hello world"

def test_string_with_numbers():
    toks = lex('"abc123"')
    assert toks[0].value == "abc123"


# ── numbers ───────────────────────────────────────────────────────

def test_integer_decimal():
    toks = lex("42")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "42"

def test_integer_zero():
    toks = lex("0")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "0"

def test_integer_hex():
    toks = lex("0xFF")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "0xFF"

def test_integer_hex_uppercase():
    toks = lex("0XFF")
    assert toks[0].type == TokensType.INTEGER

def test_integer_hex_full():
    # all hex digits
    toks = lex("0xABCDEF0123456789")
    assert toks[0].type == TokensType.INTEGER

def test_integer_hex_lowercase():
    toks = lex("0xabcdef")
    assert toks[0].type == TokensType.INTEGER

def test_integer_binary():
    toks = lex("0b1010")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "0b1010"

def test_integer_binary_uppercase():
    toks = lex("0B1010")
    assert toks[0].type == TokensType.INTEGER

def test_integer_octal():
    toks = lex("0o77")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "0o77"

def test_integer_octal_uppercase():
    toks = lex("0O77")
    assert toks[0].type == TokensType.INTEGER

def test_float():
    toks = lex("3.14")
    assert toks[0].type  == TokensType.FLOAT
    assert toks[0].value == "3.14"

def test_float_zero():
    toks = lex("0.0")
    assert toks[0].type == TokensType.FLOAT

def test_not_float_trailing_dot():
    toks = lex("3.")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "3"


# ── registers — general purpose ───────────────────────────────────

def test_register_uppercase():
    toks = lex("EAX")
    assert toks[0].type == TokensType.REGISTER

def test_register_lowercase():
    toks = lex("eax")
    assert toks[0].type  == TokensType.REGISTER
    assert toks[0].value == "EAX"

# 8-bit
@pytest.mark.parametrize("reg", ["AL","AH","BL","BH","CL","CH","DL","DH"])
def test_registers_8bit(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER

# 16-bit
@pytest.mark.parametrize("reg", ["AX","BX","CX","DX","SI","DI","SP","BP"])
def test_registers_16bit(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER

# 32-bit
@pytest.mark.parametrize("reg", ["EAX","EBX","ECX","EDX","ESI","EDI","ESP","EBP"])
def test_registers_32bit(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER

# 64-bit
@pytest.mark.parametrize("reg", ["RAX","RBX","RCX","RDX","RSI","RDI","RSP","RBP"])
def test_registers_64bit(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER


# ── registers — control ───────────────────────────────────────────

@pytest.mark.parametrize("reg", ["CR0","CR1","CR2","CR3","CR4"])
def test_registers_control(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER


# ── registers — flags ─────────────────────────────────────────────

@pytest.mark.parametrize("reg", ["ZF","CF","OF","SF"])
def test_registers_flags(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER


# ── registers — instruction pointers ─────────────────────────────

@pytest.mark.parametrize("reg", ["IP","EIP","RIP"])
def test_registers_instruction_pointers(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER


# ── registers — segments ──────────────────────────────────────────

@pytest.mark.parametrize("reg", ["CS","DS","SS","FS","GS"])
def test_registers_segments(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER


# ── registers — SIMD / vector ─────────────────────────────────────

@pytest.mark.parametrize("reg", ["MMX0","MMX1","MMX2","MMX3","MMX4","MMX5","MMX6","MMX7"])
def test_registers_mmx(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER

@pytest.mark.parametrize("reg", ["k0","k1","k2","k3","k4","k6","k7"])
def test_registers_avx_mask(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER

def test_register_fpc_mxcsr():
    toks = lex("MXCSR")
    assert toks[0].type == TokensType.REGISTER


# ── registers — ELB (extended low byte) ──────────────────────────

@pytest.mark.parametrize("reg", ["SIL","DIL","BPL","SPL","R8B","R9B","R10B","R11B"])
def test_registers_elb(reg):
    toks = lex(reg)
    assert toks[0].type == TokensType.REGISTER


# ── size hints ────────────────────────────────────────────────────

@pytest.mark.parametrize("hint", ["BYTE","WORD","DWORD","QWORD"])
def test_size_hints(hint):
    toks = lex(hint)
    assert toks[0].type == TokensType.SIZE_HINT

def test_size_hint_lowercase():
    toks = lex("qword")
    assert toks[0].type  == TokensType.SIZE_HINT
    assert toks[0].value == "QWORD"


# ── directives ────────────────────────────────────────────────────

@pytest.mark.parametrize("directive", [
    "BITS","SECTION","GLOBAL","EXTERN",
    "DB","DW","DD","DQ",
    "RESB","RESW","RESD","RESQ",
    "EQU","TIMES","ALIGN","ORG",
])
def test_directives(directive):
    toks = lex(directive)
    assert toks[0].type == TokensType.DERECTIVE

def test_directive_lowercase():
    toks = lex("section")
    assert toks[0].type == TokensType.DERECTIVE


# ── labels ───────────────────────────────────────────────────────

def test_label_def():
    toks = lex("main:")
    assert toks[0].type  == TokensType.LABEL_DEF
    assert toks[0].value == "main"

def test_label_preserves_case():
    toks = lex("MyLabel:")
    assert toks[0].value == "MyLabel"

def test_label_with_underscore():
    toks = lex("_start:")
    assert toks[0].type  == TokensType.LABEL_DEF
    assert toks[0].value == "_start"

def test_label_with_dot():
    toks = lex(".loop:")
    assert toks[0].type  == TokensType.LABEL_DEF
    assert toks[0].value == ".loop"


# ── mnemonics ─────────────────────────────────────────────────────

@pytest.mark.parametrize("mnemonic", [
    # data movement
    "MOV", "MOVZX", "MOVSX", "MOVSXD", "LEA", "XCHG", "PUSH", "POP",
    # arithmetic
    "ADD", "SUB", "MUL", "IMUL", "DIV", "IDIV", "INC", "DEC", "NEG",
    "ADC", "SBB",
    # logic
    "AND", "OR", "XOR", "NOT", "SHL", "SHR", "SAR", "ROL", "ROR",
    # comparison / jumps
    "CMP", "TEST", "JMP", "JE", "JNE", "JZ", "JNZ", "JG", "JL",
    "JGE", "JLE", "JA", "JB", "JAE", "JBE",
    # calls
    "CALL", "RET", "LEAVE", "ENTER",
    # misc
    "NOP", "HLT", "SYSCALL", "INT",
    # SIMD — MMX
    "MOVQ", "PADDB", "PADDW", "PADDD", "PSUBB", "PSUBW", "PSUBD",
    "PMULLW", "PAND", "POR", "PXOR", "PCMPEQB",
    # SIMD — SSE
    "MOVAPS", "MOVUPS", "MOVSS", "ADDPS", "SUBPS", "MULPS", "DIVPS",
    "ADDSS", "SUBSS", "MULSS", "DIVSS", "SQRTPS", "MAXPS", "MINPS",
    "CMPPS", "SHUFPS", "UNPCKLPS", "UNPCKHPS",
    # SIMD — SSE2
    "MOVAPD", "MOVUPD", "MOVSD", "ADDPD", "SUBPD", "MULPD", "DIVPD",
    "ADDSD", "SUBSD", "MULSD", "DIVSD", "SQRTPD",
    "MOVDQA", "MOVDQU", "PADDQ", "PSUBQ", "PMULUDQ",
    # SIMD — SSE3 / SSSE3
    "HADDPS", "HSUBPS", "MOVSHDUP", "MOVSLDUP",
    "PABSB", "PABSW", "PABSD", "PHADDW", "PHADDD",
    # SIMD — SSE4
    "PMULLD", "PMULDQ", "PBLENDW", "PBLENDVB",
    "PCMPEQQ", "PCMPGTQ", "PMINSD", "PMINSB",
    "INSERTPS", "EXTRACTPS", "DPPS", "DPPD",
    # AVX
    "VMOVAPS", "VMOVUPS", "VADDPS", "VSUBPS", "VMULPS", "VDIVPS",
    "VADDPD", "VSUBPD", "VMULPD", "VDIVPD",
    "VPAND", "VPOR", "VPXOR", "VPCMPEQB",
])
def test_mnemonics(mnemonic):
    toks = lex(mnemonic)
    assert toks[0].type  == TokensType.MNEMONIC
    assert toks[0].value == mnemonic

def test_mnemonic_lowercase():
    toks = lex("mov")
    assert toks[0].type  == TokensType.MNEMONIC
    assert toks[0].value == "MOV"


# ── punctuation ───────────────────────────────────────────────────

def test_punct_lbracket():
    assert types("[") == [TokensType.LBRACKET]

def test_punct_rbracket():
    assert types("]") == [TokensType.RBRACKET]

def test_punct_plus():
    assert types("+") == [TokensType.PLUS]

def test_punct_minus():
    assert types("-") == [TokensType.MINUS]

def test_punct_star():
    assert types("*") == [TokensType.STAR]

def test_punct_comma():
    assert types(",") == [TokensType.COMMA]

def test_punct_colon():
    assert types(":") == [TokensType.COLON]


# ── full real x86_64 instructions ────────────────────────────────

def test_mov_reg_reg():
    assert types("MOV EAX, EBX") == [
        TokensType.MNEMONIC,
        TokensType.REGISTER,
        TokensType.COMMA,
        TokensType.REGISTER,
    ]

def test_mov_reg_imm():
    assert types("MOV RAX, 42") == [
        TokensType.MNEMONIC,
        TokensType.REGISTER,
        TokensType.COMMA,
        TokensType.INTEGER,
    ]

def test_mov_mem_reg():
    assert types("MOV [EBX], EAX") == [
        TokensType.MNEMONIC,
        TokensType.LBRACKET,
        TokensType.REGISTER,
        TokensType.RBRACKET,
        TokensType.COMMA,
        TokensType.REGISTER,
    ]

def test_mov_reg_mem_offset():
    assert types("MOV EAX, [EBX+4]") == [
        TokensType.MNEMONIC,
        TokensType.REGISTER,
        TokensType.COMMA,
        TokensType.LBRACKET,
        TokensType.REGISTER,
        TokensType.PLUS,
        TokensType.INTEGER,
        TokensType.RBRACKET,
    ]

def test_mov_size_hint():
    assert types("MOV DWORD [EBX], 1") == [
        TokensType.MNEMONIC,
        TokensType.SIZE_HINT,
        TokensType.LBRACKET,
        TokensType.REGISTER,
        TokensType.RBRACKET,
        TokensType.COMMA,
        TokensType.INTEGER,
    ]

def test_lea_instruction():
    assert types("LEA RAX, [RBX+RCX*4]") == [
        TokensType.MNEMONIC,
        TokensType.REGISTER,
        TokensType.COMMA,
        TokensType.LBRACKET,
        TokensType.REGISTER,
        TokensType.PLUS,
        TokensType.REGISTER,
        TokensType.STAR,
        TokensType.INTEGER,
        TokensType.RBRACKET,
    ]

def test_push_pop():
    assert types("PUSH RAX") == [TokensType.MNEMONIC, TokensType.REGISTER]
    assert types("POP  RBX") == [TokensType.MNEMONIC, TokensType.REGISTER]

def test_add_instruction():
    assert types("ADD EAX, 1") == [
        TokensType.MNEMONIC,
        TokensType.REGISTER,
        TokensType.COMMA,
        TokensType.INTEGER,
    ]

def test_cmp_and_jump():
    assert types("CMP EAX, 0") == [
        TokensType.MNEMONIC,
        TokensType.REGISTER,
        TokensType.COMMA,
        TokensType.INTEGER,
    ]
    assert types("JE .done") == [
        TokensType.MNEMONIC,
        TokensType.MNEMONIC,   # .done is a label ref, not defined yet → MNEMONIC
    ]

def test_simd_movaps():
    assert types("MOVAPS MMX0, MMX1") == [
        TokensType.MNEMONIC,
        TokensType.REGISTER,
        TokensType.COMMA,
        TokensType.REGISTER,
    ]

def test_syscall():
    assert types("SYSCALL") == [TokensType.MNEMONIC]

def test_nop():
    assert types("NOP") == [TokensType.MNEMONIC]

def test_ret():
    assert types("RET") == [TokensType.MNEMONIC]


# ── full real programs ────────────────────────────────────────────

def test_full_hello_world_structure():
    source = """\
; hello world skeleton
SECTION .data
    msg DB "hello", 0
SECTION .text
GLOBAL _start
_start:
    MOV RAX, 1
    MOV RDI, 1
    MOV RSI, msg
    MOV RDX, 5
    SYSCALL
    MOV RAX, 60
    XOR RDI, RDI
    SYSCALL
"""
    toks = lex(source)
    tok_types = [t.type for t in toks]
    assert TokensType.DERECTIVE  in tok_types   # SECTION, DB, GLOBAL
    assert TokensType.LABEL_DEF  in tok_types   # _start:
    assert TokensType.MNEMONIC   in tok_types   # MOV, SYSCALL, XOR
    assert TokensType.REGISTER   in tok_types   # RAX, RDI, RSI, RDX
    assert TokensType.INTEGER    in tok_types   # 1, 60, 5
    assert TokensType.STRING     in tok_types   # "hello"

def test_full_loop_structure():
    source = """\
; simple counter loop
    MOV ECX, 10
.loop:
    DEC ECX
    JNZ .loop
"""
    toks = lex(source)
    tok_types = [t.type for t in toks]
    assert TokensType.MNEMONIC  in tok_types
    assert TokensType.REGISTER  in tok_types
    assert TokensType.INTEGER   in tok_types
    assert TokensType.LABEL_DEF in tok_types

def test_full_function_prologue():
    source = """\
my_func:
    PUSH RBP
    MOV  RBP, RSP
    SUB  RSP, 32
"""
    toks = lex(source)
    tok_types = [t.type for t in toks]
    assert TokensType.LABEL_DEF in tok_types
    assert TokensType.MNEMONIC  in tok_types
    assert TokensType.REGISTER  in tok_types
    assert TokensType.INTEGER   in tok_types

def test_full_simd_block():
    source = """\
; SIMD addition
    MOVAPS MMX0, MMX1
    PADDD  MMX0, MMX2
    MOVQ   [RAX], MMX0
"""
    toks = lex(source)
    tok_types = [t.type for t in toks]
    assert TokensType.MNEMONIC  in tok_types
    assert TokensType.REGISTER  in tok_types


# ── unexpected character ──────────────────────────────────────────

def test_unexpected_char():
    with pytest.raises(SyntaxError):
        Lexer("@invalid").tokenize()

def test_unexpected_char_hash():
    with pytest.raises(SyntaxError):
        Lexer("#define").tokenize()

def test_unexpected_char_dollar_alone():
    with pytest.raises(SyntaxError):
        Lexer("$").tokenize()
