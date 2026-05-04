bits 16
org 0x7C00

_start:
    mov ah, 0x0E    
    mov al, 0x48    
    int 0x10        
    
    mov al, 0x69    
    int 0x10
    
    mov al, 0x21    
    int 0x10

.hang:
    hlt             
    jmp .hang       

; Hardcoded padding instead of NASM math:
resb 492  
dw 0xAA55
