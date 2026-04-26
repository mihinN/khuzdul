# main.py or cli.py
from assembler.lexer         import Lexer
from assembler.parser        import Parser
from assembler.symbol_table  import SymbolTable

source  = open("hello.asm").read()
tokens  = Lexer(source).tokenize()
program = Parser(tokens).parse()

# build symbol table
sym_table = SymbolTable(base_address=0)
sym_table.build(program)
sym_table.dump()

# now encoder can ask:
offset = sym_table.offset_of("_start")   # 0x00
offset = sym_table.offset_of("loop")     # 0x10
offset = sym_table.offset_of("msg")      # 0x20