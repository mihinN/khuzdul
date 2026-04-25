sofisticated assembler 

https://events.static.linuxfound.org/sites/events/files/slides/bpetkov-x86-hacks.pdf



x86 ISA
- little endian byteorder 
- CISC (Hybrid : Complex Instruction Set Computer)
- variable length max , 15 byte long (120bits)

Legacy Prefix | REX | Opcode | ModRM | SIB | Displacement | Immediate 

- REX slot will replace with VEX or EVEX when we are dealing with Vector instructions

- Encoder 
    * legacy prefix 
    * rex 
    * vex 
    * evex 
    * opcode 
    * modrm 
    * sib 
    * displacement 
    * immediate 

- Attack surface 
    * Instruction Boundary Desync 
    * Overalpping Instructions 
    * Prefix Abuse 
    * REX Prefix Abuse 
    * Segment Override Confusion 
    * The 15limit as a DOS 
    * Spectre and Meltdown 
    * SMSW / Privilaged Instruction sumgling 

- Because of these reasons, we have to validate instructions. 
- Architecture 

assembly_code -> <lexing and parsing> -> encoding instructions -> <check opcode and operands>
* Operands have : raw instruction , type , base register , index reg , scale and displacement 


- Lexer Logic 

