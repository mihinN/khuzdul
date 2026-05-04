# test/test_new_opcodes.py

from assembler.lexer  import Lexer
from assembler.parser import Parser
from assembler.tokens import TokensType
from assembler.ir     import OperandType


def lex(source):
    return Lexer(source).tokenize()


def parse(source):
    tokens  = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    return program


# ── lexer ────────────────────────────────────────────────

class TestLexerNewMnemonics:

    def test_movsx_is_mnemonic(self):
        tokens = lex("movsx eax, bx\n")
        assert tokens[0].type  == TokensType.MNEMONIC
        assert tokens[0].value == "MOVSX"

    def test_movzx_is_mnemonic(self):
        tokens = lex("movzx eax, bl\n")
        assert tokens[0].type  == TokensType.MNEMONIC
        assert tokens[0].value == "MOVZX"

    def test_adc_is_mnemonic(self):
        tokens = lex("adc eax, ebx\n")
        assert tokens[0].type  == TokensType.MNEMONIC
        assert tokens[0].value == "ADC"

    def test_test_is_mnemonic(self):
        tokens = lex("test eax, eax\n")
        assert tokens[0].type  == TokensType.MNEMONIC
        assert tokens[0].value == "TEST"

    def test_bt_is_mnemonic(self):
        tokens = lex("bt eax, 1\n")
        assert tokens[0].type  == TokensType.MNEMONIC
        assert tokens[0].value == "BT"

    def test_cmpxchg_is_mnemonic(self):
        tokens = lex("cmpxchg [ebx], eax\n")
        assert tokens[0].type  == TokensType.MNEMONIC
        assert tokens[0].value == "CMPXCHG"

    def test_pushf_is_mnemonic(self):
        tokens = lex("pushf\n")
        assert tokens[0].type  == TokensType.MNEMONIC
        assert tokens[0].value == "PUSHF"

    def test_in_is_mnemonic(self):
        tokens = lex("in al, dx\n")
        assert tokens[0].type  == TokensType.MNEMONIC
        assert tokens[0].value == "IN"


# ── parser ───────────────────────────────────────────────

class TestParserNewMnemonics:

    def test_movsx_parses(self):
        p = parse("movsx eax, bx\n")
        i = p.instructions()[0]
        assert i.mnemonic          == "MOVSX"
        assert len(i.operands)     == 2
        assert i.operands[0].value == "EAX"
        assert i.operands[1].value == "BX"

    def test_movzx_parses(self):
        p = parse("movzx eax, bl\n")
        i = p.instructions()[0]
        assert i.mnemonic      == "MOVZX"
        assert len(i.operands) == 2

    def test_adc_parses(self):
        p = parse("adc eax, ebx\n")
        i = p.instructions()[0]
        assert i.mnemonic      == "ADC"
        assert len(i.operands) == 2

    def test_test_parses(self):
        p = parse("test eax, eax\n")
        i = p.instructions()[0]
        assert i.mnemonic      == "TEST"
        assert len(i.operands) == 2

    def test_bt_parses(self):
        p = parse("bt eax, 1\n")
        i = p.instructions()[0]
        assert i.mnemonic                  == "BT"
        assert i.operands[1].op_type       == OperandType.IMMEDIATE

    def test_cmpxchg_parses(self):
        p = parse("cmpxchg [ebx], eax\n")
        i = p.instructions()[0]
        assert i.mnemonic                  == "CMPXCHG"
        assert i.operands[0].op_type       == OperandType.MEMORY
        assert i.operands[1].op_type       == OperandType.REGISTER

    def test_pushf_no_operands(self):
        p = parse("pushf\n")
        i = p.instructions()[0]
        assert i.mnemonic      == "PUSHF"
        assert len(i.operands) == 0

    def test_in_parses(self):
        p = parse("in al, dx\n")
        i = p.instructions()[0]
        assert i.mnemonic      == "IN"
        assert len(i.operands) == 2

    def test_out_parses(self):
        p = parse("out dx, al\n")
        i = p.instructions()[0]
        assert i.mnemonic      == "OUT"
        assert len(i.operands) == 2
