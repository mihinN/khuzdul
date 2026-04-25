class Registers: 
    def __init__(self):
        # hope to use named tuples, but not today 
        # AL: Lower 4bits and AH for higher 4bits 
        # FPC : Floating point control : MXCSR
        # ELB : Extended Low Byte : 32bit
        self.R_8 = ("AL", "AH", "BL", "BH", "CL", "CH", "DL", "DH")
        self.ELB = ("SIL", "DIL", "BPL", "SPL", "R8B", "R9B", "R10B", "R11B", "R12B", "R13B", "R14B", "R15B")
        self.R_16 = ("AX", "BX", "CX", "DX", "SI", "DI", "SP", "BP")
        self.SEGMENT = ("CS", "DS", "SS", "FS", "GS")
        self.R_32 = ("EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "ESP", "EBP")
        self.R_64 = ("RAX", "RBX", "RCX", "RDX", "RSI", "RDI", "RSP", "RBP")
        self.FLAGS = ("ZF", "CF", "OF", "SF")
        self.RFLAGS = ("ZF", "CF", "OF", "SF")
        self.IP_16 = ("IP",)
        self.IP_32 = ("EIP",)
        self.IP_64 = ("RIP",)
        self.CONTROL = ("CR0", "CR1", "CR2", "CR3", "CR4", "CR5", "CR6", "CR7", "CR8")
        self.DEBUG = ("DR0", "DR1", "DR2", "DR3", "DR4", "DR5", "DR6", "DR7")
        self.SIMD = ("MMX0", "MMX1", "MMX2", "MMX3", "MMX4", "MMX5", "MMX6", "MMX7")
        self.AVX = ("K0", "K1", "K2", "K3", "K4", "K6", "K7")
        self.FPC = ("MXCSR",)

    # TODO: 80bit registers, 128, 256, 512bit vector registers
    def show_r8_reg(self) -> tuple:
        return self.R_8

    def show_r16_reg(self) -> tuple:
        return self.R_16