from assembler.tokens import Tokens, TokensType
from isa.instructions import Instructions
from isa.registers import Registers

_R = Registers()
# testing features in the lexer 
REGISTERS_CONTROL    = _R.CONTROL
REGISTERS_DATA       = _R.R_8 + _R.R_16 + _R.R_32 + _R.R_64
REGISTER_FLAGS       = _R.FLAGS + _R.RFLAGS
REGISTER_VECTOR      = _R.SIMD + _R.AVX + _R.FPC
INSTRUCTION_POINTERS = _R.IP_16 + _R.IP_32 + _R.IP_64
SEGMENTS             = _R.SEGMENT
ELB                  = _R.ELB

ALL_REGISTERS = set(
    REGISTERS_CONTROL    +
    REGISTERS_DATA       +
    REGISTER_FLAGS       +
    REGISTER_VECTOR      +
    INSTRUCTION_POINTERS +
    SEGMENTS             +
    ELB
)

SIZE = {"BYTE", "WORD", "DWORD", "QWORD"}

DIRECTIVES = {
    "BITS", "SECTION", "GLOBAL", "EXTERN",
    "DB", "DW", "DD", "DQ",
    "RESB", "RESW", "RESD", "RESQ",
    "EQU", "TIMES", "ALIGN", "ORG",
    # TODO: STRUC, ENDSTRUC, MACRO, ENDMACRO
    # TODO: %IF %ELSE %ENDIF %INCBIN %WARNING %ERROR
    # TODO: %DEFINE %INCLUDE
    # CHECK: list_of_directives.txt
}


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.position = 0 # cursor position
        self.line = 1
        self.colmn = 1
        self.tokens = []

    def tokenize(self):
        while not self._at_end():
            self._scan_tokens()
        self._add(TokensType.EOF, "")
        return self.tokens

    def _scan_tokens(self):
        self._skip_whitespaces()
        if self._at_end():
            return
        ch = self._peek()

        # mapping tokens with Tokentype : tokens.py , grabbing characters and moving forward in source
        if ch == ";": self._comment()
        elif ch == "\n": self._newline()
        elif ch == "[": self._single(TokensType.LBRACKET)
        elif ch == "]": self._single(TokensType.RBRACKET)
        elif ch == "+": self._single(TokensType.PLUS)
        elif ch == "-": self._single(TokensType.MINUS)
        elif ch == "*": self._single(TokensType.STAR)
        elif ch == ",": self._single(TokensType.COMMA)
        elif ch == ":": self._single(TokensType.COLON)
        elif ch == '"': self._string()
        elif ch.isdigit(): self._number()
        elif ch.isalpha() or ch in "_.": self._identifier()
        else:
            raise SyntaxError(
                f"[{self.line}:{self.colmn}] unexpected '{ch}'"
            )

    # **** Scanner ****
    # regx for loosers, we leave that in professional way

    def _comment(self):
        # checking comments
        start = self.position
        while not self._at_end() and self._peek() != "\n":
            self._peek_advance()
        self._add(TokensType.COMMENTS, self.source[start:self.position])

    def _newline(self):
        # new line checking
        self._peek_advance()
        self._add(TokensType.NEWLINE, "\n")
        self.line += 1
        self.colmn = 1

    def _string(self):
        self._peek_advance()                     # skip opening "
        start = self.position
        while not self._at_end() and self._peek() != '"':
            self._peek_advance()
        if self._at_end():                       # ← AFTER the loop
            raise SyntaxError(
                f"[{self.line}:{self.colmn}] unterminated string"
            )
        value = self.source[start:self.position]
        self._peek_advance()                     # skip closing "
        self._add(TokensType.STRING, value)

    def _number(self):
        # checking numbers
        # start -> number_type -> if_0x -> if_0b -> if_0o -> if_decimal -> if_float
        # what about negative numbers ?? we decide negative numbers in the parser
        # finalize the tokentype : Integer or Float
        start  = self.position
        prefix = self._peek_next().lower()

        if self._peek() == "0" and prefix in "xbo":
            self._peek_advance(); self._peek_advance()  # skip 0x/0b/0o

            if prefix == "x":
                while not self._at_end() and self._peek() in "0123456789abcdefABCDEF":
                    self._peek_advance()
            elif prefix == "b":
                while not self._at_end() and self._peek() in "01":
                    self._peek_advance()
            elif prefix == "o":
                while not self._at_end() and self._peek() in "01234567":
                    self._peek_advance()

            self._add(TokensType.INTEGER, self.source[start:self.position])
            return

        # decimal / float
        while not self._at_end() and self._peek().isdigit():
            self._peek_advance()

        if not self._at_end() and self._peek() == "." and self._peek_next().isdigit():
            self._peek_advance()                 # consume "."
            while not self._at_end() and self._peek().isdigit():
                self._peek_advance()
            self._add(TokensType.FLOAT, self.source[start:self.position])
            return

        self._add(TokensType.INTEGER, self.source[start:self.position])

    def _identifier(self):
        # identifier : this is for word like tokens like : ".section/.SECTION , MOV , SUB , main: , first_name, label_1"
        # get_word -> consuming_all_characters -> extract_uppercase (uppercase for comparision)
        """
        decision tree
        is_it_register ? -> EAX, RBX, AH, AL
        is_it_size_hint ? -> "BYTE",WORD , DWORD
        is_it_directive ? -> DB , SECTION , GLOBAL
        label_or_what ? -> followed by ":"
        NONE -> MNEMONIC or ??
        """
        start = self.position
        while not self._at_end() and (
            self._peek().isalnum() or self._peek() in "_$."
        ):
            self._peek_advance()
        value = self.source[start:self.position]
        upper = value.upper()

        if upper in ALL_REGISTERS:
            self._add(TokensType.REGISTER, upper)
        elif upper in SIZE:
            self._add(TokensType.SIZE_HINT, upper)
        elif upper in DIRECTIVES:
            self._add(TokensType.DERECTIVE, upper)
        elif self._peek() == ":":
            self._peek_advance()
            self._add(TokensType.LABEL_DEF, value)
        else:
            self._add(TokensType.MNEMONIC, upper)

    # **** helper functions ****

    def _skip_whitespaces(self):
        while not self._at_end() and self._peek() in " \t\r":
            # we leave "\n" because in asm newlines are important
            self._peek_advance()

    def _single(self, type: TokensType):
        # for single charcters , grab the character and moves to the forward
        self._add(type, self._peek_advance())

    def _add(self, type: TokensType, value: str):
        # package into tokens and store it
        self.tokens.append(Tokens(type, value, self.line, self.colmn))

    # Lookahead patterns
    def _peek(self):
        # print("return current character , no move")
        return "\0" if self._at_end() else self.source[self.position]

    def _peek_next(self):
        # print("return next character")
        if self.position + 1 >= len(self.source):
            return "\0"
        return self.source[self.position + 1]

    def _peek_advance(self):
        # print("return current character and mov position to the forward")
        ch = self.source[self.position]
        self.position += 1
        self.colmn += 1
        return ch

    def _at_end(self):
        return self.position >= len(self.source)