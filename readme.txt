Khuzdul 
/* koozdul */ 

khuzdul is a x86_64 custom, educational, strictly two-pass x86-64 assembler written entirely in Python. 
It translates x86-64 assembly source code directly into raw, flat machine-code binaries (`.bin`). 

Unlike standard assemblers (like NASM or GAS) that prioritize complex object file generation (ELF/PE),
"Khuz" is designed with a strong focus on security research, reverse engineering, and shellcode development. 
Its Intermediate Representation (IR) layer includes built-in constructs for shellcode constraints, 
such as badchar filtering and position-independent code (PIC) verification.

in parser using simple grammar like Recursive Descent LL1 parsing.
currently this generates raw binaries only and hope to add ELF, PE in future.
adding extra complexity (IR and symbol layer) for shellcode engine. easy to optimize with that. 

this project still in alpha stage an dong development in future with free time.
and these are the limitations: 
- no JMP shortneing (check this:)
- no Floating point Operations 
- no Math expressions 
- no Sementic Validations

add these on next stages. 

* **Raw Flat Binary Output:** Perfect for testing shellcode, writing bootloaders, or executing raw memory payloads.
* **x86-64 Instruction Support:** Handles a wide array of General Purpose, Control Flow, SIMD (SSE/AVX), and Bit Manipulation instructions.
* **Complex Memory Operands:** Fully supports SIB (Scale-Index-Base) addressing forms (e.g., `[EBX + ECX*4 + 8]`) and `RIP`-relative addressing.
* **Data Directives:** Supports `DB`, `DW`, `DD`, `DQ`, and buffer reservation (`RESB`, `RESW`, etc.).
* **Shellcode Constraints (IR Layer):** Infrastructure to eventually enforce `BADCHARS`, size limits, and `AVOID_NULL` encoding preferences natively.


still there is no creative , already added tested theories , parsing and lexing techniques. just build a pipeline 
to get raw binaries out of x86 assembly instructions.