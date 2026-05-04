# Instructions

class Instructions:

    GPA_OPS = {
        "ADD":     [b"\x00", b"\x01", b"\x02", b"\x03", b"\x04", b"\x05", b"\x80", b"\x81", b"\x83"],
            # add with carry
        "ADC":     [b"\x10", b"\x11", b"\x12", b"\x13", b"\x14", b"\x15", b"\x80", b"\x81", b"\x83"],
        "SUB":     [b"\x28", b"\x29", b"\x2B", b"\x2C", b"\x2D", b"\x81", b"\x83"],
            # substract with borrow
        "SUBB":    [b"\x81", b"\x83"],
        "MUL":     [b"\xF7", b"\x69", b"\x6B", b"\x0F\xAF"],
        "DIV/IDIV":[b"\xF6", b"\xF7"],
        "INC/DEC": [b"\xFF", b"\x40", b"\x41", b"\x42", b"\x43", b"\x44", b"\x45", b"\x46", b"\x47"],
        "NEG":     [b"\xF7"],
        "AND":     [b"\x20", b"\x21", b"\x22", b"\x23", b"\x25", b"\x80", b"\x81", b"\x83"],
        "OR":      [b"\x08", b"\x09", b"\x0B", b"\x0D", b"\x80", b"\x81", b"\x83"],
        "XOR":     [b"\x30", b"\x31", b"\x32", b"\x33", b"\x35", b"\x80", b"\x81", b"\x83"],
        "NOT":     [b"\xF6", b"\xF7"],
        "TEST":    [b"\x84", b"\x85", b"\xA9", b"\xF6", b"\xF7"],
        "CMP":     [b"\x38", b"\x39", b"\x3A", b"\x3B", b"\x3C", b"\x3D", b"\x80", b"\x81", b"\x83"],
    }

    # Data Transfer
    DATA_T = {
        "MOV":            [b"\x89", b"\x8A", b"\x8B", b"\x8C", b"\x8E", b"\xA0", b"\xA1", b"\xA2", b"\xA3", b"\xC6", b"\xC7",
                           b"\xA4", b"\xA5",
                           b"\xB0", b"\xB1", b"\xB2", b"\xB3", b"\xB4", b"\xB5", b"\xB6", b"\xB7",
                           b"\xB8", b"\xB9", b"\xBA", b"\xBB", b"\xBC", b"\xBD", b"\xBE", b"\xBF"],
        "MOVSX":          [b"\x0F\xBE", b"\x0F\xBF"],
        "MOVZX":          [b"\x0F\xB6", b"\x0F\xB7"],
        "MOVBE":          [b"\x0F\x38\xF0", b"\x0F\x38\xF1"],
        "MOVD/MOVQ":      [b"\x0F\x6E", b"\x0F\x7E", b"\x0F\x6F", b"\x0F\x7F"],
        "PUSH":           [b"\x50", b"\x51", b"\x52", b"\x53", b"\x54", b"\x55", b"\x56", b"\x57", b"\x68", b"\x6A", b"\xFF",
                           b"\x06", b"\x0E", b"\x16", b"\x1E"],
        "POP":            [b"\x58", b"\x59", b"\x5A", b"\x5B", b"\x5C", b"\x5D", b"\x5E", b"\x5F", b"\x8F",
                           b"\x07", b"\x17", b"\x1F"],
        "PUSHA/PUSHAD":   [b"\x60"],
        "PUSHF/POPF":     [b"\x9C", b"\x9D"],
        "CMPXCHG":        [b"\x0F\xB0", b"\x0F\xB1"],
        "CMPXCHG8B/16B":  [b"\x0F\xC7"],
        "LES/LFS/LGS/LSS":[b"\xC4", b"\x0F\xB4", b"\x0F\xB5", b"\x0F\xB2"],
        "IN":             [b"\xE5", b"\xEC", b"\xED"],
        "OUT":            [b"\xE7", b"\xEE", b"\xEF"],
    }

    # Control Flow Instructions
    CFI = {
        "CALL":   [b"\xE8", b"\xFF", b"\x9A"],
        "RET":    [b"\xC3", b"\xC2"],
        "RETF":   [b"\xCB", b"\xCA"],
        "JMP":    [b"\xEB", b"\xE9", b"\xFF", b"\xEA"],
        "Jcc":    [b"\x70", b"\x71", b"\x72", b"\x73", b"\x74", b"\x75", b"\x76", b"\x77",
                   b"\x78", b"\x79", b"\x7A", b"\x7B", b"\x7C", b"\x7D", b"\x7E", b"\x7F",
                   b"\x0F\x80", b"\x0F\x81", b"\x0F\x82", b"\x0F\x83", b"\x0F\x84", b"\x0F\x85",
                   b"\x0F\x86", b"\x0F\x87", b"\x0F\x88", b"\x0F\x89", b"\x0F\x8A", b"\x0F\x8B",
                   b"\x0F\x8C", b"\x0F\x8D", b"\x0F\x8E", b"\x0F\x8F"],
        "LOOP":   [b"\xE2"],
        "LOOPE":  [b"\xE1"],
        "LOOPNE": [b"\xE0"],
        "CMOVcc": [b"\x0F\x41", b"\x0F\x42", b"\x0F\x43", b"\x0F\x44", b"\x0F\x45",
                   b"\x0F\x46", b"\x0F\x47", b"\x0F\x48", b"\x0F\x49", b"\x0F\x4A",
                   b"\x0F\x4B", b"\x0F\x4C", b"\x0F\x4D", b"\x0F\x4E", b"\x0F\x4F"],
    }

    # Bit Manipulation
    BIT_MANI = {
        "BT":       [b"\x0F\xA3", b"\x0F\xBA"],
        "BTC":      [b"\x0F\xBB"],
        "BTR":      [b"\x0F\xB3"],
        "BTS":      [b"\x0F\xAB"],
        "BSR":      [b"\x0F\xBD"],
        "ROL/ROR":  [b"\xC0", b"\xC1", b"\xD0", b"\xD1", b"\xD2", b"\xD3"],
        "RCL/RCR":  [b"\xC0", b"\xC1", b"\xD0", b"\xD1", b"\xD2", b"\xD3"],
        "SHL/SHR":  [b"\xC1", b"\xD1", b"\xD3"],
        "SHLD/SHRD":[b"\x0F\xA4", b"\x0F\xA5", b"\x0F\xAC", b"\x0F\xAD"],
        "VEX Bits (BZHI/MULX/PDEP/PEXT/SARX/SHLX/SHRX/RORX)": [b"\xC4"],
        "XOP Bits (BLCI/BLCS/T1MSKC/TZMSK)":                   [b"\x8F"],
    }

    # SIMD (SSE)
    SSE = {
            # SIMD Floating Point (SSE/AVX)
        "ADDPS/ADDPD":          [b"\x58"],
        "SUBPS/SUBPD":          [b"\x5C"],
        "MULPS/MULPD/MULSS/MULSD": [b"\x59"],
        "DIVPS/DIVPD":          [b"\x5E"],
        "ANDPS/ANDPD":          [b"\x54"],
        "ANDNPS/ANDNPD":        [b"\x55"],
        "ORPS/ORPD":            [b"\x56"],
        "CMPPS/CMPPD/CMPSS/CMPSD": [b"\xC2"],
        "UCOMISD/UCOMISS":      [b"\x2E"],

        # SIMD Data Movement
        "MOVAPS/MOVAPD":        [b"\x28", b"\x29"],
        "MOVUPS/MOVUPD":        [b"\x10", b"\x11"],
        "MOVSS/MOVSD":          [b"\x10", b"\x11"],
        "MOVDQA/MOVDQU":        [b"\x6F", b"\x7F"],
        "MOVLPS":               [b"\x12"],
        "MOVNTDQ":              [b"\xE7"],
        "MOVNTDQA":             [b"\x2A"],
        "MOVNTPS/MOVNTPD":      [b"\x2B"],

        # SIMD Packed Integer Math
        "PADDB/W/D/Q":          [b"\xFC", b"\xFD", b"\xFE", b"\xD4"],
        "PADDSx":               [b"\xEC", b"\xED"],
        "PSUBx":                [b"\xF8", b"\xF9", b"\xFA", b"\xFB"],
        "PMULDQ":               [b"\x28"],
        "PMULHUW/PMULHW":       [b"\xE4", b"\xE5"],
        "PMULLD/PMULLW":        [b"\x40", b"\xD5"],
        "PAND":                 [b"\xDB"],
        "PANDN":                [b"\xDF"],
        "POR":                  [b"\xEB"],
        "PXOR":                 [b"\xEF"],

        # SIMD Shuffle Permute Unpack
        "PSHUFB":               [b"\x00"],
        "PSHUFD/HW/LW":         [b"\x70"],
        "PUNPCKHigh":           [b"\x68", b"\x69", b"\x6A", b"\x6D"],
        "PUNPCKLow":            [b"\x60", b"\x61", b"\x62", b"\x6C"],
        "VSHUFPD":              [b"\xC6"],

        # SIMD Vector Shifts
        "PSLLx":                [b"\x71", b"\x72", b"\x73", b"\xF1", b"\xF2", b"\xF3"],
        "PSRAx":                [b"\x71", b"\x72", b"\xE1", b"\xE2"],
        "PSRLx":                [b"\x71", b"\x72", b"\x73", b"\xD1", b"\xD2", b"\xD3"],

        # AVX-512 Opmask
        "KMOVB/W/D/Q":          [b"\x90", b"\x91", b"\x92", b"\x93"],
        "KORTEST":              [b"\x98"],
        "KTEST":                [b"\x99"],
        "KSHIFTL/KSHIFTR":      [b"\x30", b"\x31", b"\x32", b"\x33"],
    }

    # System instructions (NOP, HALT and stuff)
    SYSTEM_INS = {
        "NOP": [b"\x90"],
        "HLT": [b"\xF4"],
        "CLAC": [b"\x0F\x01\xCA"],
        "MOV CRn": [b"\x0F\x20", b"\x0F\x22"],
        "RDPMC": [b"\x0F\x33"],
        "RDFSBBASE/RDGSBASE": [b"\xF3\x0F\xAE"],
        "WRSS/WRUSS": [b"\x0F\x38\xF6"],
        "CMPCCxADD": [b"\xE0", b"\xE1", b"\xE2", b"\xE3", b"\xE4", b"\xE5",b"\xE6", b"\xE7", b"\xE8", b"\xE9", b"\xEA", b"\xEB", b"\xEC"],
    }