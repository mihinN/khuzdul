# Tokens 
from enum import Enum, auto

# Token names
class TokensType(Enum): 
    # Instructions 
    MNEMONIC = auto()
    # Operands 
    REGISTER = auto() # eax, ebx 
    INTEGER = auto() 
    FLOAT = auto()
    STRING = auto()
    # Memory 
        ## []
    LBRACKET = auto()
    RBRACKET = auto() 
    # Operators 
        # + , - , * , : 
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    COLON = auto()
    # Structures 
        # , new_line /n(0x0A) , EOF (end of file different from systems - windows , linux , mac , 
        # and modern systems follows new approach)
    COMMA = auto()
    NEWLINE = auto()
    EOF = auto()
    # Symbols 
    LABEL_DEF = auto() # label definition like loop: , _start: just declared the label, 
    LABEL_REF = auto() # label is used as jump target or address 
    DERECTIVE = auto() # not cpu instrucstion , tell assembler what to do 
    # Size 
    SIZE_HINT = auto()
    # Comments 
    COMMENTS = auto()

class Tokens: 
    def __init__(self, type: TokensType, value: str, line: int , column: int):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return(
            f"Token("
            f"type= {self.type.name}, "
            f"value= {self.value!r}", 
            f"line= {self.line}", 
            f"col= {self.column}", 
            f")"
        )

    def __eq__(self, other):
        if not isinstance(other, Tokens): 
            return NotImplemented
        return (
            self.type == other.type and self.value == other.value and 
            self.line == other.line and self.column == other.column
        )
        

