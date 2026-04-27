class AssemblerError(Exception):
    """base class for all assembler errors"""
    def __init__(self, message: str, line: int = 0, column: int = 0):
        self.line   = line
        self.column = column
        super().__init__(
            f"[{line}:{column}] {message}" if line else message
        )
 
 
class LexerError(AssemblerError):
    """raised by lexer on unexpected character"""
    pass
 
 
class ParserError(AssemblerError):
    """raised by parser on unexpected token"""
    pass
 
 
class EncoderError(AssemblerError):
    """raised by encoder on unsupported instruction or operand"""
    pass
 
 
class SymbolError(AssemblerError):
    """raised by symbol table"""
    pass