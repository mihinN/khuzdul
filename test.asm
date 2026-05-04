; test.asm - Simple test for your custom SASM assembler
bits 64

_start:
    ; 1. Clear registers (your tests specifically check for no-null-byte XORs)
    xor rax, rax
    xor rdi, rdi

    ; 2. Basic data movement and arithmetic
    mov eax, 10
    add eax, 32
    sub eax, 5

    ; 3. Loop demonstration using a local label
    mov ecx, 5
.loop:
    dec ecx
    jnz .loop

    ; 4. Graceful exit syscall (sys_exit = 60)
    mov al, 60
    xor rdi, rdi
    syscall
