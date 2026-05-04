# Khuzdul

*/koozdul/*

Khuzdul is an educational, two-pass x86-64 assembler written in pure Python. It translates x86-64 assembly source into raw flat machine-code binaries (`.bin`) - no ELF, no PE, just bytes.

Where mainstream assemblers like NASM and GAS focus on producing object files for the system linker, Khuzdul is built for **security research, reverse engineering, and shellcode development**. The IR layer carries shellcode-aware metadata (bad-character filtering, PIC verification, encoding preferences) as first-class concerns rather than afterthoughts.

> **Status:** alpha. Development happens in spare time.

## Features

- **Raw flat binary output** - suitable for shellcode, bootloaders, and direct execution from raw memory.
- **Broad x86-64 ISA coverage** - general-purpose, control flow, SIMD (SSE/AVX), and bit-manipulation instructions.
- **Full SIB addressing** - `[EBX + ECX*4 + 8]` and similar.
- **RIP-relative addressing** — `[RIP + offset]`.
- **Data directives** -  `DB`, `DW`, `DD`, `DQ`, and the reserve forms `RESB`, `RESW`, `RESD`, `RESQ`.
- **Shellcode constraint scaffolding** -  infrastructure for `BADCHARS`, `MAX_SIZE`, and `AVOID_NULL` encoding preferences. (Wiring is in progress.)

## Architecture

```
source.asm -> Lexer -> Parser -> IR  -> SymbolTable -> Encoder ->  out.bin
```

- **Lexer** - character-by-character scanner. No regex.
- **Parser** - recursive-descent (LL(1)). Assembly grammar is simple enough that a hand-written parser is clearer than a generated one.
- **IR** - instructions, labels, directives, data, plus shellcode constraints attached to the program.
- **Symbol table** - two passes. Pass 1 walks the IR sizing every instruction and recording label offsets; pass 2 resolves every `LABEL_REF` operand.
- **Encoder** - emits prefixes, REX, opcode, ModR/M, SIB, displacement, and immediate.

## Usage

```bash
python -m assembler hello.asm -o hello.bin
```

Example program:

```nasm
_start:
    xor rax, rax
    xor rdi, rdi
    inc rax
    ret
```

## Requirements

- Python 3.x

No third-party dependencies for the assembler itself. `pytest` is used for the test suite.

## Tests

```bash
pytest tests/
```

## Limitations

Current gaps. Each one is on the roadmap:

- **No jump shortening.** All `JMP`/`Jcc` instructions emit the near form (`rel32`) even when `rel8` would fit. Output is correct but not size-optimal.
- **No floating-point instructions.** x87 and FP variants of SSE are not yet wired up.
- **No expression evaluator.** Immediate operands must be literal numbers -  no `(8 * 4) + 1` or symbol arithmetic.
- **No semantic validation beyond syntax.** The assembler will happily encode `MOV AL, RAX` and produce something nonsensical.
- **Output is raw flat binary only.** ELF and PE are planned but not started.

## Roadmap

1. Branch-displacement optimization (jump shortening).
2. Expression evaluator for immediates.
3. Semantic validation pass — operand-size compatibility, register-class checks.
4. ELF and PE output.
5. Wire shellcode constraints (`BADCHARS`, `MAX_SIZE`) into the encoder so violating sequences are rejected at assembly time.
6. Floating-point support.

## License
BSD 3-Clause License. See [LICENSE](LICENSE) for the full text.

## Acknowledgements

Built as a learning project. The pipeline (lex → parse → IR → resolve → encode) is textbook, the design decisions inside each stage are mine.

This project stands on the work of engineers who designed x86, built the first assemblers and linkers, and figured it all out from scratch, no Stack Overflow, no AI, just patience and a 500-page manual.
To everyone who left knowledge behind: thank you.

"If I have seen further, it is by standing on the shoulders of giants."- Isaac Newton