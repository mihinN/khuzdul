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


# ── newline ───────────────────────────────────────────────────────

def test_newline_token():
    toks = lex("\n")
    assert toks[0].type  == TokensType.NEWLINE
    assert toks[0].value == "\n"

def test_newline_increments_line():
    tokens = Lexer("MOV\nADD").tokenize()
    add_tok = [t for t in tokens if t.value == "ADD"][0]
    assert add_tok.line == 2


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


# ── numbers ───────────────────────────────────────────────────────

def test_integer_decimal():
    toks = lex("42")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "42"

def test_integer_hex():
    toks = lex("0xFF")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "0xFF"

def test_integer_hex_uppercase():
    toks = lex("0XFF")
    assert toks[0].type == TokensType.INTEGER

def test_integer_binary():
    toks = lex("0b1010")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "0b1010"

def test_integer_octal():
    toks = lex("0o77")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "0o77"

def test_float():
    toks = lex("3.14")
    assert toks[0].type  == TokensType.FLOAT
    assert toks[0].value == "3.14"

def test_not_float_trailing_dot():
    # "3." should be INTEGER 3, then DOT as something else
    toks = lex("3.")
    assert toks[0].type  == TokensType.INTEGER
    assert toks[0].value == "3"


# ── registers ─────────────────────────────────────────────────────

def test_register_uppercase():
    toks = lex("EAX")
    assert toks[0].type == TokensType.REGISTER

def test_register_lowercase():
    toks = lex("eax")
    assert toks[0].type  == TokensType.REGISTER
    assert toks[0].value == "EAX"   # normalized to upper


# ── size hints ────────────────────────────────────────────────────

def test_size_hint_byte():
    toks = lex("BYTE")
    assert toks[0].type == TokensType.SIZE_HINT

def test_size_hint_qword():
    toks = lex("qword")
    assert toks[0].type  == TokensType.SIZE_HINT
    assert toks[0].value == "QWORD"


# ── directives ────────────────────────────────────────────────────

def test_directive_section():
    toks = lex("SECTION")
    assert toks[0].type == TokensType.DERECTIVE

def test_directive_db():
    toks = lex("db")
    assert toks[0].type == TokensType.DERECTIVE


# ── labels ───────────────────────────────────────────────────────

def test_label_def():
    toks = lex("main:")
    assert toks[0].type  == TokensType.LABEL_DEF
    assert toks[0].value == "main"

def test_label_preserves_case():
    toks = lex("MyLabel:")
    assert toks[0].value == "MyLabel"   # labels are case sensitive


# ── mnemonics ─────────────────────────────────────────────────────

def test_mnemonic_mov():
    toks = lex("MOV")
    assert toks[0].type == TokensType.MNEMONIC

def test_mnemonic_lowercase():
    toks = lex("mov")
    assert toks[0].type  == TokensType.MNEMONIC
    assert toks[0].value == "MOV"


# ── punctuation ───────────────────────────────────────────────────

def test_punctuation():
    toks = lex("[]+-, *,")
    assert types("[ ]") == [TokensType.LBRACKET, TokensType.RBRACKET]
    assert types("+")   == [TokensType.PLUS]
    assert types("-")   == [TokensType.MINUS]
    assert types("*")   == [TokensType.STAR]
    assert types(",")   == [TokensType.COMMA]


# ── full instruction ──────────────────────────────────────────────

def test_full_mov_instruction():
    toks = lex("MOV EAX, 42")
    assert types("MOV EAX, 42") == [
        TokensType.MNEMONIC,
        TokensType.REGISTER,
        TokensType.COMMA,
        TokensType.INTEGER,
    ]

def test_full_label_and_instruction():
    source = "main:\n  MOV EAX, 1"
    t = types(source)
    assert TokensType.LABEL_DEF in t
    assert TokensType.MNEMONIC  in t
    assert TokensType.REGISTER  in t
    assert TokensType.INTEGER   in t


# ── unexpected character ──────────────────────────────────────────

def test_unexpected_char():
    with pytest.raises(SyntaxError):
        Lexer("@invalid").tokenize()