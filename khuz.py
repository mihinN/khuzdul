
import argparse
import sys
from pathlib import Path

from assembler.lexer import Lexer
from assembler.parser import Parser
from assembler.symbol_table import SymbolTable
from assembler.encoder import Encoder
from assembler.error import AssemblerError

def main():
    parser = argparse.ArgumentParser(description="SASM - Simple x86-64 Assembler")
    parser.add_argument("input", help="Input assembly source file")
    parser.add_argument("-o", "--output", default="out.bin", help="Output raw binary file (default: out.bin)")
    parser.add_argument("-b", "--base", type=lambda x: int(x, 0), default=0, help="Base address/ORG (e.g., 0x400000). Default: 0.")
    parser.add_argument("--dump-ir", action="store_true", help="Print the Intermediate Representation (IR) to stdout")
    parser.add_argument("--dump-sym", action="store_true", help="Print the resolved Symbol Table to stdout")

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.is_file():
        print(f"Error: Could not find input file '{args.input}'", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            source = f.read()

        print(f"[*] Assembling '{args.input}'...")

        # Step 1: Lexical Analysis
        tokens = Lexer(source).tokenize()

        # Step 2: Parsing (Generate IR)
        program = Parser(tokens).parse()
        if args.dump_ir:
            program.dump()

        # Step 3: Symbol Resolution (Pass 1 & Pass 2)
        sym_table = SymbolTable(base_address=args.base)
        sym_table.build(program)
        if args.dump_sym:
            sym_table.dump()

        # Step 4: Encoding (Machine code generation)
        encoder = Encoder(program, sym_table)
        machine_code = encoder.encode()

        # Step 5: Write output
        with open(args.output, "wb") as f:
            f.write(machine_code)

        print(f"[+] Success! Wrote {len(machine_code)} bytes to '{args.output}'")

    # Catch custom assembler errors to print a clean error message
    except AssemblerError as e:
        print(f"\n[-] Assembly Failed:\n{e}", file=sys.stderr)
        sys.exit(1)
    # Catch raw Python errors
    except Exception as e:
        print(f"\n[-] Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()