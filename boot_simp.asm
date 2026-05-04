; boot.asm - Simple 16-bit BIOS Bootloader
bits 16
org 0x7C00          ; BIOS loads the boot sector to memory address 0x7C00

_start:
    ; Set up the BIOS teletype output (Interrupt 0x10, Function 0x0E)
    mov ah, 0x0E    
    
    ; Print 'H'
    mov al, 0x48    ; Hex for 'H'
    int 0x10        ; Call BIOS video interrupt
    
    ; Print 'i'
    mov al, 0x69    ; Hex for 'i'
    int 0x10
    
    ; Print '!'
    mov al, 0x21    ; Hex for '!'
    int 0x10

.hang:
    hlt             ; Halt CPU to save power
    jmp .hang       ; Infinite loop in case of wake-up

; --- Boot Sector Padding & Magic Number ---
; A valid boot sector MUST be exactly 512 bytes and end with 0xAA55.
; Standard NASM uses the `times` directive to automatically calculate the padding:
times 510 - ($ - $$) db 0  
dw 0xAA55           ; Boot signature
