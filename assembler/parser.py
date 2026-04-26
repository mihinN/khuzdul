# parser
# here using : Recursive Descent Parser : https://en.wikipedia.org/wiki/Recursive_descent_parser
# LL1, read left to right , 1 token lookahead
# this is good for simple grammer like assembly

# assembler/parser.py

from assembler.tokens import Tokens, TokensType
from assembler.ir import (
    IRProgram, IRInstructions, IRLabel, IRData, IRDirectives,
    Operand, OperandType, OperandSize, REGISTER_SIZE, OPCODE_TABLE
)

class Parser:
    def __init__(self, tokens: list):
        self.tokens   = tokens
        self.position = 0
        self.program  = IRProgram()

# **** parse , this loop unit end of file ****
    def parse(self) -> IRProgram:
        # print("this is parse method")
        while not self._at_end():
            node = self._parse_line()
            if node is not None:
                self.program.add(node)
        return self.program

# **** parser line , look at the one token and decide which parser to call ****
    def _parse_line(self):
        # print("deciding based on new lines and directive mnemonic")
        """
        each line is one of :
        blank / comment -> skip , return NONE
        LABEL_DEF -> IRLABEL
        DIRECTIVE args -> IRDIRECTIVE or IRDATA
        MNEMONIC operation -> IRInstruction
        """
        self._skip_newlines()               # fix: was _skip_newline()
        if self._at_end():
            return None
        tok = self._peek()
        if tok.type in (TokensType.NEWLINE, TokensType.COMMENTS):
            self._peek_advance()
            return None
        # parse label , parse directive and parse instructions
        if tok.type == TokensType.LABEL_DEF:
            return self._parse_label()
        if tok.type == TokensType.DERECTIVE:
            return self._parse_directive()
        if tok.type == TokensType.MNEMONIC:
            return self._parse_instructions()

        raise SyntaxError(
            f"[{tok.line}:{tok.column}] "
            f"unexpected token '{tok.value}' ({tok.type.name})"
        )


# **** Parse Labels ****
    def _parse_label(self) -> IRLabel:
        tok  = self._consume(TokensType.LABEL_DEF)
        node = IRLabel(
            name   = tok.value,
            line   = tok.line,
            column = tok.column,
        )
        self._skip_to_newline()             # fix: was _skip_newlines()
        return node

# **** Parse Directives ****
    def _parse_directive(self):
        """
        here handle two cases :
        01: Data Directives with a label like :
            msg DB "hello", 0
            num DB 22
        02: Plain Directives like :
            BITS 64
            GLOBAL _start
            SECTION .text
        """
        tok  = self._consume(TokensType.DERECTIVE)
        name = tok.value
            # adding data directives
        if name in ("DB", "DW", "DD", "DQ",
                    "RESB", "RESW", "RESD", "RESQ"):
            return self._parse_data(name, tok.line)
            # plain directives
        args = []
        while not self._at_end() and self._peek().type not in (
            TokensType.NEWLINE, TokensType.COMMENTS, TokensType.EOF
        ):
            args.append(self._parse_directive_arg())
            if self._peek().type == TokensType.COMMA:
                self._peek_advance()        # fix: was _advance()

        self._skip_to_newline()
        return IRDirectives(
            name   = name,
            args   = args,
            line   = tok.line,
            column = tok.column,
        )

    def _parse_data(self, directive: str, line: int):
        """
        parse:
            DB  "hello", 0x0A, 0
            DD  42
            RESB 64
        """
        size_map = {
            "DB": OperandSize.BYTE,  "RESB": OperandSize.BYTE,
            "DW": OperandSize.WORD,  "RESW": OperandSize.WORD,
            "DD": OperandSize.DWORD, "RESD": OperandSize.DWORD,
            "DQ": OperandSize.QWORD, "RESQ": OperandSize.QWORD,
        }
        size       = size_map[directive]
        values     = []
        is_reserve = directive.startswith("RES")   # ← fix: RESB/RESW/RESD/RESQ

        while not self._at_end() and self._peek().type not in (
            TokensType.NEWLINE, TokensType.COMMENTS, TokensType.EOF
        ):
            tok = self._peek()

            if tok.type == TokensType.STRING:
                self._peek_advance()        # fix: was _advance()
                values.append(tok.value)

            elif tok.type == TokensType.INTEGER:
                self._peek_advance()        # fix: was _advance()
                values.append(self._to_int(tok.value))

            elif tok.type == TokensType.MINUS:
                self._peek_advance()        # fix: was _advance()
                num = self._consume(TokensType.INTEGER)
                values.append(-self._to_int(num.value))

            elif tok.type == TokensType.COMMA:
                self._peek_advance()        # fix: was _advance()

            else:
                break

        self._skip_to_newline()
        return IRData(
            label      = None,          # label attached by symbol table pass
            size       = size,
            values     = values,
            line       = line,
            is_reserve = is_reserve,    # ← fix: pass reserve flag
        )

    def _parse_directive_arg(self):
        tok = self._peek()

        if tok.type == TokensType.INTEGER:
            self._peek_advance()            # fix: was _advance()
            return self._to_int(tok.value)

        if tok.type == TokensType.STRING:
            self._peek_advance()            # fix: was _advance()
            return tok.value

        if tok.type == TokensType.MNEMONIC:
            self._peek_advance()            # fix: was _advance()
            return tok.value                # label ref as string

        if tok.type == TokensType.REGISTER:
            self._peek_advance()            # fix: was _advance()
            return tok.value

        raise SyntaxError(
            f"[{tok.line}:{tok.column}] "
            f"unexpected directive arg '{tok.value}'"
        )

# **** Parse Instructions ****
    def _parse_instructions(self) -> IRInstructions:
        tok      = self._consume(TokensType.MNEMONIC)
        mnemonic = tok.value
        operand  = []

        # no operands , NOP , RET , HLT
        if self._peek().type in (
            TokensType.NEWLINE, TokensType.COMMENTS, TokensType.EOF
        ):
            self._skip_newlines()
            return IRInstructions(
                mnemonic = mnemonic,
                operands = [],
                line     = tok.line,
                column   = tok.column,
            )

        # first Operand
        operand.append(self._parse_operand())
        # remaining operands seperated by comma
        while self._peek().type == TokensType.COMMA:
            self._peek_advance()
            operand.append(self._parse_operand())

        self._skip_to_newline()
        return IRInstructions(
            mnemonic = mnemonic,
            operands = operand,
            line     = tok.line,
            column   = tok.column,
        )

# **** Operand ****
    def _parse_operand(self) -> Operand:
        """
        operand types:
            EAX              ->  REGISTER
            0xFF             ->  IMMEDIATE
            -1               ->  IMMEDIATE  (negative)
            _start           ->  LABEL_REF
            [EBX]            ->  MEMORY
            [EBX+ECX*4+8]    ->  MEMORY
            DWORD [EBX]      ->  MEMORY  with size hint
            DWORD PTR [EBX]  ->  MEMORY  with size hint
        """
        tok = self._peek()
        # register
        if tok.type == TokensType.REGISTER:
            self._peek_advance()            # fix: was _advance()
            size = REGISTER_SIZE.get(tok.value, OperandSize.NONE)
            op   = Operand(OperandType.REGISTER, tok.value, size)
            return op

        # immediate
        if tok.type == TokensType.INTEGER:
            self._peek_advance()            # fix: was _advance()
            value = self._to_int(tok.value)
            size  = self._imm_size(value)
            return Operand(OperandType.IMMEDIATE, value, size)

        # negative immediate
        if tok.type == TokensType.MINUS:
            self._peek_advance()            # fix: was _advance()
            num   = self._consume(TokensType.INTEGER)
            value = -self._to_int(num.value)
            size  = self._imm_size(value)
            return Operand(OperandType.IMMEDIATE, value, size)

        # size hint ->  DWORD [EBX]  or  DWORD PTR [EBX]
        if tok.type == TokensType.SIZE_HINT:
            return self._parse_memory_operand()

        # memory -> [EBX + ECX*4 + 8]
        if tok.type == TokensType.LBRACKET:
            return self._parse_memory_operand()

        # label reference  -> jmp _start / call printf
        if tok.type == TokensType.MNEMONIC:
            self._peek_advance()            # fix: was _advance()
            return Operand(OperandType.LABEL_REF, tok.value, OperandSize.NONE)

        raise SyntaxError(
            f"[{tok.line}:{tok.column}] "
            f"unexpected operand '{tok.value}' ({tok.type.name})"
        )

# **** Memory Operands ****
    def _parse_memory_operand(self) -> Operand:
        """
        handles:
            [EBX]
            [EBX + 8]
            [EBX + ECX]
            [EBX + ECX*4]
            [EBX + ECX*4 + 8]
            DWORD [EBX]
            DWORD PTR [EBX + ECX*4 + 8]
            [RIP + offset]      ← rip relative
        """
        size_hint = OperandSize.NONE

        # consume size hint if present
        if self._peek().type == TokensType.SIZE_HINT:
            hint_map = {
                "BYTE":  OperandSize.BYTE,
                "WORD":  OperandSize.WORD,
                "DWORD": OperandSize.DWORD,
                "QWORD": OperandSize.QWORD,
            }
            hint_tok  = self._peek_advance()  # fix: was _advance()
            size_hint = hint_map.get(hint_tok.value, OperandSize.NONE)

            # optional PTR keyword
            if (
                self._peek().type  == TokensType.MNEMONIC and
                self._peek().value == "PTR"
            ):
                self._peek_advance()          # fix: was _advance()

        self._consume(TokensType.LBRACKET)

        base  = None
        index = None
        scale = 1
        disp  = 0

        # first term
        if self._peek().type == TokensType.REGISTER:
            reg = self._peek_advance().value  # fix: was _advance()

            if self._peek().type == TokensType.STAR:
                # index*scale form  e.g. [ECX*4]
                self._peek_advance()          # fix: was _advance()
                scale = self._to_int(self._consume(TokensType.INTEGER).value)
                index = reg
            else:
                base = reg

        elif self._peek().type == TokensType.INTEGER:
            disp = self._to_int(self._peek_advance().value)  # fix: was _advance()

        # remaining term
        while self._peek().type in (TokensType.PLUS, TokensType.MINUS):
            sign = 1 if self._peek_advance().type == TokensType.PLUS else -1
            tok  = self._peek()

            if tok.type == TokensType.REGISTER:
                reg = self._peek_advance().value  # fix: was _advance()

                if self._peek().type == TokensType.STAR:
                    self._peek_advance()          # fix: was _advance()
                    sc    = self._to_int(self._consume(TokensType.INTEGER).value)
                    index = reg
                    scale = sc
                else:
                    if base is None:
                        base = reg
                    else:
                        index = reg

            elif tok.type == TokensType.INTEGER:
                disp += sign * self._to_int(self._peek_advance().value)

            else:
                raise SyntaxError(
                    f"[{tok.line}:{tok.column}] "
                    f"unexpected token in memory operand '{tok.value}'"
                )

        self._consume(TokensType.RBRACKET)

        # build operand
        op            = Operand(OperandType.MEMORY, None, size_hint)
        op.base       = base
        op.index      = index
        op.scale      = scale
        op.disp       = disp

        # rip relative detection
        if base == "RIP":
            op.is_rip_relative = True

        return op

# **** helper functions ****
    def _to_int(self, value: str) -> int:
        return int(value, 0)    # handles 0x, 0b, 0o

    def _imm_size(self, value: int) -> int:
        if -128        <= value <= 255:        return OperandSize.BYTE
        if -32768      <= value <= 65535:      return OperandSize.WORD
        if -2147483648 <= value <= 4294967295: return OperandSize.DWORD
        return OperandSize.QWORD

    def _skip_newlines(self):
        while not self._at_end() and self._peek().type == TokensType.NEWLINE:
            self._peek_advance()

    def _skip_to_newline(self):
        while not self._at_end() and self._peek().type not in (
            TokensType.NEWLINE, TokensType.EOF
        ):
            if self._peek().type == TokensType.COMMENTS:
                self._peek_advance()
                break
            self._peek_advance()

    # **** Lookahead patterns ****
    def _peek(self) -> Tokens:
        return self.tokens[self.position]

    def _peek_next(self) -> Tokens:
        if self.position + 1 >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.position + 1]

    def _peek_advance(self) -> Tokens:
        tok = self.tokens[self.position]
        if not self._at_end():
            self.position += 1
        return tok

    def _consume(self, expected: TokensType) -> Tokens:
        tok = self._peek()
        if tok.type != expected:
            raise SyntaxError(
                f"[{tok.line}:{tok.column}] "
                f"expected {expected.name} "
                f"got '{tok.value}' ({tok.type.name})"
            )
        return self._peek_advance()

    def _at_end(self) -> bool:
        return self.tokens[self.position].type == TokensType.EOF  # fix: was self.pos