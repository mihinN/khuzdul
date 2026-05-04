# test/test_encoder.py
# unit tests for assembler/encoder.py
# tests individual encoding functions + full instruction encoding
# verified against known x86 encodings

import pytest
import struct

from assembler.lexer         import Lexer
from assembler.parser        import Parser
from assembler.symbol_table  import SymbolTable
from assembler.encoder       import (
    Encoder,
    EncodedInstruction,
    encode_rex,
    encode_modrm,
    encode_sib,
    encode_displacement,
    encode_immediate,
    encode_legacy_prefix,
)
from assembler.error import EncoderError


# **** helpers ****

def assemble(source: str, base: int = 0) -> bytes:
    tokens  = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    sym     = SymbolTable(base_address=base)
    sym.build(program)
    return Encoder(program, sym).encode()


# ════════════════════════════════════════════════════════════
# 1 — EncodedInstruction container
# ════════════════════════════════════════════════════════════

class TestEncodedInstruction:

    def test_empty_to_bytes(self):
        enc = EncodedInstruction()
        assert enc.to_bytes() == b""

    def test_opcode_only(self):
        enc = EncodedInstruction()
        enc.opcode = b"\x90"
        assert enc.to_bytes() == b"\x90"

    def test_correct_order(self):
        # legacy prefix must come before REX
        # REX before opcode
        # opcode before ModRM
        enc = EncodedInstruction()
        enc.legacy_prefix = b"\x66"
        enc.rex           = b"\x48"
        enc.opcode        = b"\x89"
        enc.modrm         = b"\xC3"
        assert enc.to_bytes() == b"\x66\x48\x89\xC3"

    def test_15_byte_limit_raises(self):
        enc = EncodedInstruction()
        enc.legacy_prefix = b"\x66\x67\xF0\xF2"
        enc.rex           = b"\x48"
        enc.opcode        = b"\x0F\x38\xF0"
        enc.modrm         = b"\xC3"
        enc.sib           = b"\x00"
        enc.displacement  = b"\x00\x00\x00\x00"
        enc.immediate     = b"\x00\x00\x00\x00"
        with pytest.raises(EncoderError, match="15 byte"):
            enc.to_bytes()

    def test_repr(self):
        enc = EncodedInstruction()
        enc.opcode = b"\x90"
        assert "90" in repr(enc)


# ════════════════════════════════════════════════════════════
# 2 — encode_legacy_prefix
# ════════════════════════════════════════════════════════════

class TestEncodeLegacyPrefix:

    def test_no_prefix(self):
        assert encode_legacy_prefix() == b""

    def test_operand_size_override(self):
        assert encode_legacy_prefix(operand_size_override=True) == b"\x66"

    def test_address_size_override(self):
        assert encode_legacy_prefix(address_size_override=True) == b"\x67"

    def test_lock_prefix(self):
        assert encode_legacy_prefix(lock=True) == b"\xF0"

    def test_rep_prefix(self):
        assert encode_legacy_prefix(rep=True) == b"\xF3"

    def test_repne_prefix(self):
        assert encode_legacy_prefix(repne=True) == b"\xF2"

    def test_lock_before_operand_size(self):
        result = encode_legacy_prefix(lock=True, operand_size_override=True)
        assert result == b"\xF0\x66"

    def test_repne_before_operand_size(self):
        result = encode_legacy_prefix(repne=True, operand_size_override=True)
        assert result == b"\xF2\x66"


# ════════════════════════════════════════════════════════════
# 3 — encode_rex
# ════════════════════════════════════════════════════════════

class TestEncodeRex:

    def test_no_rex_when_all_false(self):
        assert encode_rex() == b""

    def test_rex_w(self):
        # REX.W = 0100 1000 = 0x48
        assert encode_rex(w=True) == b"\x48"

    def test_rex_r(self):
        # REX.R = 0100 0100 = 0x44
        assert encode_rex(r=True) == b"\x44"

    def test_rex_x(self):
        # REX.X = 0100 0010 = 0x42
        assert encode_rex(x=True) == b"\x42"

    def test_rex_b(self):
        # REX.B = 0100 0001 = 0x41
        assert encode_rex(b=True) == b"\x41"

    def test_rex_wr(self):
        # REX.WR = 0100 1100 = 0x4C
        assert encode_rex(w=True, r=True) == b"\x4C"

    def test_rex_wxb(self):
        # REX.WXB = 0100 1011 = 0x4B
        assert encode_rex(w=True, x=True, b=True) == b"\x4B"

    def test_rex_all(self):
        # REX.WRXB = 0100 1111 = 0x4F
        assert encode_rex(w=True, r=True, x=True, b=True) == b"\x4F"

    def test_rex_always_starts_with_0x4(self):
        result = encode_rex(w=True)
        assert result[0] & 0xF0 == 0x40

    def test_rex_is_single_byte(self):
        assert len(encode_rex(w=True, r=True, x=True, b=True)) == 1


# ════════════════════════════════════════════════════════════
# 4 — encode_modrm
# ════════════════════════════════════════════════════════════

class TestEncodeModRM:

    def test_reg_to_reg_eax_ebx(self):
        # mod=11 reg=000(EAX) rm=011(EBX) = 1100 0011 = 0xC3
        assert encode_modrm(0b11, 0b000, 0b011) == b"\xC3"

    def test_reg_to_reg_ebx_eax(self):
        # mod=11 reg=011(EBX) rm=000(EAX) = 1101 1000 = 0xD8
        assert encode_modrm(0b11, 0b011, 0b000) == b"\xD8"

    def test_mem_no_disp(self):
        # mod=00 reg=000 rm=011 = 0000 0011 = 0x03
        assert encode_modrm(0b00, 0b000, 0b011) == b"\x03"

    def test_mem_disp8(self):
        # mod=01 reg=000 rm=011 = 0100 0011 = 0x43
        assert encode_modrm(0b01, 0b000, 0b011) == b"\x43"

    def test_mem_disp32(self):
        # mod=10 reg=000 rm=011 = 1000 0011 = 0x83
        assert encode_modrm(0b10, 0b000, 0b011) == b"\x83"

    def test_sib_indicator(self):
        # rm=100 signals SIB byte follows
        assert encode_modrm(0b00, 0b000, 0b100) == b"\x04"

    def test_all_zeros(self):
        assert encode_modrm(0, 0, 0) == b"\x00"

    def test_all_max(self):
        # mod=11 reg=111 rm=111 = 1111 1111 = 0xFF
        assert encode_modrm(0b11, 0b111, 0b111) == b"\xFF"

    def test_mod_out_of_range_raises(self):
        with pytest.raises(AssertionError):
            encode_modrm(4, 0, 0)

    def test_reg_out_of_range_raises(self):
        with pytest.raises(AssertionError):
            encode_modrm(0, 8, 0)

    def test_rm_out_of_range_raises(self):
        with pytest.raises(AssertionError):
            encode_modrm(0, 0, 8)

    def test_is_single_byte(self):
        assert len(encode_modrm(0b11, 0b000, 0b011)) == 1


# ════════════════════════════════════════════════════════════
# 5 — encode_sib
# ════════════════════════════════════════════════════════════

class TestEncodeSIB:

    def test_scale1_index_ecx_base_ebx(self):
        # scale=1(00) index=001 base=011 = 0000 1011 = 0x0B
        assert encode_sib(1, 0b001, 0b011) == b"\x0B"

    def test_scale2(self):
        # scale=2(01) index=001 base=011 = 0100 1011 = 0x4B
        assert encode_sib(2, 0b001, 0b011) == b"\x4B"

    def test_scale4(self):
        # scale=4(10) index=001 base=011 = 1000 1011 = 0x8B
        assert encode_sib(4, 0b001, 0b011) == b"\x8B"

    def test_scale8(self):
        # scale=8(11) index=001 base=011 = 1100 1011 = 0xCB
        assert encode_sib(8, 0b001, 0b011) == b"\xCB"

    def test_invalid_scale_raises(self):
        with pytest.raises(EncoderError):
            encode_sib(3, 0, 0)

    def test_invalid_scale_5_raises(self):
        with pytest.raises(EncoderError):
            encode_sib(5, 0, 0)

    def test_is_single_byte(self):
        assert len(encode_sib(4, 0b001, 0b011)) == 1


# ════════════════════════════════════════════════════════════
# 6 — encode_displacement
# ════════════════════════════════════════════════════════════

class TestEncodeDisplacement:

    def test_no_displacement(self):
        assert encode_displacement(0, 0) == b""

    def test_disp8_positive(self):
        assert encode_displacement(8, 1) == b"\x08"

    def test_disp8_max(self):
        assert encode_displacement(127, 1) == b"\x7F"

    def test_disp8_negative(self):
        assert encode_displacement(-1, 1) == b"\xFF"

    def test_disp32_positive(self):
        assert encode_displacement(0x1000, 4) == struct.pack("<i", 0x1000)

    def test_disp32_negative(self):
        assert encode_displacement(-4, 4) == struct.pack("<i", -4)

    def test_disp32_little_endian(self):
        assert encode_displacement(0x12345678, 4) == b"\x78\x56\x34\x12"

    def test_invalid_size_raises(self):
        with pytest.raises(EncoderError):
            encode_displacement(0, 2)

    def test_invalid_size_3_raises(self):
        with pytest.raises(EncoderError):
            encode_displacement(0, 3)


# ════════════════════════════════════════════════════════════
# 7 — encode_immediate
# ════════════════════════════════════════════════════════════

class TestEncodeImmediate:

    def test_imm8_one(self):
        assert encode_immediate(1, 1) == b"\x01"

    def test_imm8_max(self):
        assert encode_immediate(127, 1) == b"\x7F"

    def test_imm8_negative(self):
        assert encode_immediate(-1, 1) == b"\xFF"

    def test_imm16_little_endian(self):
        assert encode_immediate(0x1234, 2) == b"\x34\x12"

    def test_imm32_little_endian(self):
        assert encode_immediate(0x12345678, 4) == b"\x78\x56\x34\x12"

    def test_imm64_little_endian(self):
        assert encode_immediate(1, 8) == b"\x01\x00\x00\x00\x00\x00\x00\x00"

    def test_imm32_deadbeef(self):
        assert encode_immediate(0xDEADBEEF, 4) == b"\xEF\xBE\xAD\xDE"

    def test_invalid_size_raises(self):
        with pytest.raises(EncoderError):
            encode_immediate(0, 3)

    def test_invalid_size_5_raises(self):
        with pytest.raises(EncoderError):
            encode_immediate(0, 5)


# ════════════════════════════════════════════════════════════
# 8 — simple no-operand instructions
# ════════════════════════════════════════════════════════════

class TestSimpleInstructions:

    def test_nop(self):
        assert assemble("nop\n") == b"\x90"

    def test_ret(self):
        assert assemble("ret\n") == b"\xC3"

    def test_hlt(self):
        assert assemble("hlt\n") == b"\xF4"

    def test_syscall(self):
        assert assemble("syscall\n") == b"\x0F\x05"

    def test_syscall_is_2_bytes(self):
        assert len(assemble("syscall\n")) == 2

    def test_multiple_nops(self):
        assert assemble("nop\nnop\nnop\n") == b"\x90\x90\x90"

    def test_ret_after_nop(self):
        assert assemble("nop\nret\n") == b"\x90\xC3"


# ════════════════════════════════════════════════════════════
# 9 — MOV register to register
# ════════════════════════════════════════════════════════════

class TestMovRegReg:

    def test_mov_ebx_eax(self):
        assert assemble("mov ebx, eax\n") == b"\x89\xC3"

    def test_mov_eax_ebx(self):
        assert assemble("mov eax, ebx\n") == b"\x89\xD8"

    def test_mov_ecx_edx(self):
        assert assemble("mov ecx, edx\n") == b"\x89\xD1"

    def test_mov_esi_edi(self):
        assert assemble("mov esi, edi\n") == b"\x89\xFE"

    def test_mov_rbp_rsp(self):
        assert assemble("mov rbp, rsp\n") == b"\x48\x89\xE5"

    def test_mov_rsp_rbp(self):
        assert assemble("mov rsp, rbp\n") == b"\x48\x89\xEC"

    def test_mov_rax_rbx(self):
        assert assemble("mov rax, rbx\n") == b"\x48\x89\xD8"

    def test_mov_rdi_rsi(self):
        assert assemble("mov rdi, rsi\n") == b"\x48\x89\xF7"

    def test_mov_32bit_no_rex(self):
        result = assemble("mov eax, ebx\n")
        assert result[0] != 0x48

    def test_mov_64bit_has_rex_w(self):
        result = assemble("mov rax, rbx\n")
        assert result[0] == 0x48

    @pytest.mark.parametrize("dst,src,expected", [
        ("EAX", "EBX", b"\x89\xD8"),
        ("EBX", "EAX", b"\x89\xC3"),
        ("ECX", "EDX", b"\x89\xD1"),
        ("EDX", "ECX", b"\x89\xCA"),
        ("ESP", "EBP", b"\x89\xEC"),
        ("EBP", "ESP", b"\x89\xE5"),
        ("ESI", "EDI", b"\x89\xFE"),
        ("EDI", "ESI", b"\x89\xF7"),
    ])
    def test_mov_r32_parametrized(self, dst, src, expected):
        assert assemble(f"mov {dst.lower()}, {src.lower()}\n") == expected


# ════════════════════════════════════════════════════════════
# 10 — MOV register immediate
# ════════════════════════════════════════════════════════════

class TestMovRegImm:

    def test_mov_eax_1(self):
        assert assemble("mov eax, 1\n") == b"\xB8\x01\x00\x00\x00"

    def test_mov_eax_0(self):
        assert assemble("mov eax, 0\n") == b"\xB8\x00\x00\x00\x00"

    def test_mov_eax_hex(self):
        assert assemble("mov eax, 0x12345678\n") == b"\xB8\x78\x56\x34\x12"

    def test_mov_ecx_imm(self):
        assert assemble("mov ecx, 10\n") == b"\xB9\x0A\x00\x00\x00"

    def test_mov_al_imm8(self):
        assert assemble("mov al, 0x42\n") == b"\xB0\x42"

    def test_mov_bl_imm8(self):
        assert assemble("mov bl, 0xFF\n") == b"\xB3\xFF"

    def test_mov_rax_has_rex_w(self):
        result = assemble("mov rax, 1\n")
        assert result[0] == 0x48
        assert result[1] == 0xB8

    def test_mov_rax_imm_is_10_bytes(self):
        # REX(1) + opcode(1) + imm64(8)
        assert len(assemble("mov rax, 1\n")) == 10


# ════════════════════════════════════════════════════════════
# 11 — PUSH / POP
# ════════════════════════════════════════════════════════════

class TestPushPop:

    def test_push_rax(self):
        assert assemble("push rax\n") == b"\x50"

    def test_push_rbx(self):
        assert assemble("push rbx\n") == b"\x53"

    def test_push_rcx(self):
        assert assemble("push rcx\n") == b"\x51"

    def test_push_rdx(self):
        assert assemble("push rdx\n") == b"\x52"

    def test_push_rbp(self):
        assert assemble("push rbp\n") == b"\x55"

    def test_push_rsp(self):
        assert assemble("push rsp\n") == b"\x54"

    def test_push_rsi(self):
        assert assemble("push rsi\n") == b"\x56"

    def test_push_rdi(self):
        assert assemble("push rdi\n") == b"\x57"

    def test_pop_rax(self):
        assert assemble("pop rax\n") == b"\x58"

    def test_pop_rbp(self):
        assert assemble("pop rbp\n") == b"\x5D"

    def test_pop_rbx(self):
        assert assemble("pop rbx\n") == b"\x5B"

    def test_push_imm8(self):
        assert assemble("push 1\n") == b"\x6A\x01"

    def test_push_imm32(self):
        assert assemble("push 256\n") == b"\x68\x00\x01\x00\x00"

    def test_push_negative(self):
        assert assemble("push -1\n") == b"\x6A\xFF"

    def test_prologue_bytes(self):
        result = assemble("push rbp\nmov rbp, rsp\n")
        assert result[0] == 0x55
        assert result[1] == 0x48
        assert result[2] == 0x89
        assert result[3] == 0xE5

    def test_epilogue_bytes(self):
        result = assemble("pop rbp\nret\n")
        assert result[0] == 0x5D
        assert result[1] == 0xC3


# ════════════════════════════════════════════════════════════
# 12 — ADD
# ════════════════════════════════════════════════════════════

class TestAdd:

    def test_add_eax_ebx(self):
        assert assemble("add eax, ebx\n") == b"\x01\xD8"

    def test_add_ebx_eax(self):
        assert assemble("add ebx, eax\n") == b"\x01\xC3"

    def test_add_ecx_edx(self):
        assert assemble("add ecx, edx\n") == b"\x01\xD1"

    def test_add_rax_rbx(self):
        assert assemble("add rax, rbx\n") == b"\x48\x01\xD8"

    def test_add_eax_imm8(self):
        assert assemble("add eax, 1\n") == b"\x83\xC0\x01"

    def test_add_eax_imm32(self):
        assert assemble("add eax, 256\n") == b"\x81\xC0\x00\x01\x00\x00"

    def test_add_rax_imm8(self):
        assert assemble("add rax, 1\n") == b"\x48\x83\xC0\x01"

    def test_add_rsp_imm8(self):
        # common stack cleanup
        assert assemble("add rsp, 32\n") == b"\x48\x83\xC4\x20"


# ════════════════════════════════════════════════════════════
# 13 — SUB
# ════════════════════════════════════════════════════════════

class TestSub:

    def test_sub_eax_ebx(self):
        assert assemble("sub eax, ebx\n") == b"\x29\xD8"

    def test_sub_rax_rbx(self):
        assert assemble("sub rax, rbx\n") == b"\x48\x29\xD8"

    def test_sub_eax_imm8(self):
        assert assemble("sub eax, 1\n") == b"\x83\xE8\x01"

    def test_sub_eax_imm32(self):
        assert assemble("sub eax, 256\n") == b"\x81\xE8\x00\x01\x00\x00"

    def test_sub_rsp_imm8(self):
        # common stack allocation
        assert assemble("sub rsp, 40\n") == b"\x48\x83\xEC\x28"

    def test_sub_rsp_32(self):
        assert assemble("sub rsp, 32\n") == b"\x48\x83\xEC\x20"


# ════════════════════════════════════════════════════════════
# 14 — XOR
# ════════════════════════════════════════════════════════════

class TestXor:

    def test_xor_eax_eax(self):
        assert assemble("xor eax, eax\n") == b"\x31\xC0"

    def test_xor_rax_rax(self):
        assert assemble("xor rax, rax\n") == b"\x48\x31\xC0"

    def test_xor_rdi_rdi(self):
        assert assemble("xor rdi, rdi\n") == b"\x48\x31\xFF"

    def test_xor_rsi_rsi(self):
        assert assemble("xor rsi, rsi\n") == b"\x48\x31\xF6"

    def test_xor_rdx_rdx(self):
        assert assemble("xor rdx, rdx\n") == b"\x48\x31\xD2"

    def test_xor_eax_imm8(self):
        assert assemble("xor eax, 0xFF\n") == b"\x83\xF0\xFF"

    def test_xor_zeroing_no_nulls(self):
        # classic shellcode pattern — xor to zero without null bytes
        result = assemble("xor rax, rax\nxor rdi, rdi\nxor rsi, rsi\n")
        assert result == b"\x48\x31\xC0\x48\x31\xFF\x48\x31\xF6"
        assert b"\x00" not in result


# ════════════════════════════════════════════════════════════
# 15 — AND / OR / CMP
# ════════════════════════════════════════════════════════════

class TestAndOrCmp:

    def test_and_eax_ebx(self):
        assert assemble("and eax, ebx\n") == b"\x21\xD8"

    def test_or_eax_ebx(self):
        assert assemble("or eax, ebx\n") == b"\x09\xD8"

    def test_cmp_eax_ebx(self):
        assert assemble("cmp eax, ebx\n") == b"\x39\xD8"

    def test_cmp_eax_imm8(self):
        assert assemble("cmp eax, 0\n") == b"\x83\xF8\x00"

    def test_cmp_rax_imm8(self):
        assert assemble("cmp rax, 0\n") == b"\x48\x83\xF8\x00"

    def test_and_eax_imm8(self):
        assert assemble("and eax, 0x0F\n") == b"\x83\xE0\x0F"

    def test_or_eax_imm8(self):
        assert assemble("or eax, 1\n") == b"\x83\xC8\x01"

    def test_cmp_rax_rbx(self):
        assert assemble("cmp rax, rbx\n") == b"\x48\x39\xD8"


# ════════════════════════════════════════════════════════════
# 16 — INC / DEC
# ════════════════════════════════════════════════════════════

class TestIncDec:

    def test_inc_eax(self):
        assert assemble("inc eax\n") == b"\xFF\xC0"

    def test_inc_ecx(self):
        assert assemble("inc ecx\n") == b"\xFF\xC1"

    def test_inc_edx(self):
        assert assemble("inc edx\n") == b"\xFF\xC2"

    def test_dec_eax(self):
        assert assemble("dec eax\n") == b"\xFF\xC8"

    def test_dec_ecx(self):
        assert assemble("dec ecx\n") == b"\xFF\xC9"

    def test_inc_rax(self):
        assert assemble("inc rax\n") == b"\x48\xFF\xC0"

    def test_dec_rcx(self):
        assert assemble("dec rcx\n") == b"\x48\xFF\xC9"

    def test_dec_rsp(self):
        assert assemble("dec rsp\n") == b"\x48\xFF\xCC"


# ════════════════════════════════════════════════════════════
# 17 — NEG / NOT
# ════════════════════════════════════════════════════════════

class TestNegNot:

    def test_neg_eax(self):
        assert assemble("neg eax\n") == b"\xF7\xD8"

    def test_not_eax(self):
        assert assemble("not eax\n") == b"\xF7\xD0"

    def test_neg_ecx(self):
        assert assemble("neg ecx\n") == b"\xF7\xD9"

    def test_not_ecx(self):
        assert assemble("not ecx\n") == b"\xF7\xD1"

    def test_neg_rax(self):
        assert assemble("neg rax\n") == b"\x48\xF7\xD8"

    def test_not_rcx(self):
        assert assemble("not rcx\n") == b"\x48\xF7\xD1"


# ════════════════════════════════════════════════════════════
# 18 — shifts
# ════════════════════════════════════════════════════════════

class TestShifts:

    def test_shl_eax_1(self):
        assert assemble("shl eax, 1\n") == b"\xD1\xE0"

    def test_shl_eax_2(self):
        assert assemble("shl eax, 2\n") == b"\xC1\xE0\x02"

    def test_shr_eax_1(self):
        assert assemble("shr eax, 1\n") == b"\xD1\xE8"

    def test_shr_eax_4(self):
        assert assemble("shr eax, 4\n") == b"\xC1\xE8\x04"

    def test_sar_eax_1(self):
        assert assemble("sar eax, 1\n") == b"\xD1\xF8"

    def test_rol_eax_1(self):
        assert assemble("rol eax, 1\n") == b"\xD1\xC0"

    def test_ror_eax_1(self):
        assert assemble("ror eax, 1\n") == b"\xD1\xC8"

    def test_shl_rax_1(self):
        assert assemble("shl rax, 1\n") == b"\x48\xD1\xE0"

    def test_shr_rax_4(self):
        assert assemble("shr rax, 4\n") == b"\x48\xC1\xE8\x04"


# ════════════════════════════════════════════════════════════
# 19 — jumps
# ════════════════════════════════════════════════════════════

class TestJumps:

    def test_jmp_starts_with_e9(self):
        result = assemble("_start:\n    jmp end\nend:\n    ret\n")
        assert result[0] == 0xE9

    def test_jmp_backward_loop(self):
        result = assemble("loop:\n    nop\n    jmp loop\n")
        assert result[0] == 0x90
        assert result[1] == 0xE9

    def test_jnz_opcode(self):
        result = assemble("_start:\n    dec ecx\n    jnz _start\n")
        assert result[2] == 0x0F
        assert result[3] == 0x85

    def test_je_opcode(self):
        result = assemble("_start:\n    nop\n    je end\nend:\n    ret\n")
        assert result[1] == 0x0F
        assert result[2] == 0x84

    def test_jz_same_as_je(self):
        s1 = "_start:\n    nop\n    jz end\nend:\n    ret\n"
        s2 = "_start:\n    nop\n    je end\nend:\n    ret\n"
        assert assemble(s1) == assemble(s2)

    def test_jnz_same_as_jne(self):
        s1 = "_start:\n    nop\n    jnz end\nend:\n    ret\n"
        s2 = "_start:\n    nop\n    jne end\nend:\n    ret\n"
        assert assemble(s1) == assemble(s2)

    def test_call_opcode(self):
        result = assemble("_start:\n    call func\n    ret\nfunc:\n    ret\n")
        assert result[0] == 0xE8

    def test_jmp_to_next_rel32_is_zero(self):
        # jmp end where end is immediately after jmp
        # rel32 = target - (offset + 5) = 5 - 5 = 0
        result = assemble("_start:\n    jmp end\nend:\n    ret\n")
        rel32 = struct.unpack("<i", result[1:5])[0]
        assert rel32 == 0

    def test_backward_jmp_rel32_negative(self):
        # loop: nop(1 byte) jmp loop
        # jmp at offset 1, target at offset 0
        # rel32 = 0 - (1 + 5) = -6
        result = assemble("loop:\n    nop\n    jmp loop\n")
        rel32 = struct.unpack("<i", result[2:6])[0]
        assert rel32 == -6

    def test_all_jcc_opcodes(self):
        jcc_map = {
            "JO": 0x80, "JNO": 0x81, "JB": 0x82, "JNB": 0x83,
            "JE": 0x84, "JZ": 0x84, "JNE": 0x85, "JNZ": 0x85,
            "JBE": 0x86, "JA": 0x87, "JS": 0x88, "JNS": 0x89,
            "JP": 0x8A, "JNP": 0x8B, "JL": 0x8C, "JGE": 0x8D,
            "JLE": 0x8E, "JG": 0x8F,
        }
        for mnemonic, opcode2 in jcc_map.items():
            source = f"_s:\n    nop\n    {mnemonic.lower()} end\nend:\n    ret\n"
            result = assemble(source)
            assert result[1] == 0x0F,    f"{mnemonic} missing 0F prefix"
            assert result[2] == opcode2, f"{mnemonic} wrong second opcode byte"


# ════════════════════════════════════════════════════════════
# 20 — data directives
# ════════════════════════════════════════════════════════════

class TestDataDirectives:

    def test_db_byte(self):
        assert assemble("db 0x41\n") == b"\x41"

    def test_db_zero(self):
        assert assemble("db 0\n") == b"\x00"

    def test_db_string(self):
        assert assemble('db "hi"\n') == b"hi"

    def test_db_string_with_null(self):
        assert assemble('db "hi", 0\n') == b"hi\x00"

    def test_db_multiple(self):
        assert assemble("db 1, 2, 3\n") == b"\x01\x02\x03"

    def test_dw_little_endian(self):
        assert assemble("dw 0x1234\n") == b"\x34\x12"

    def test_dd_little_endian(self):
        assert assemble("dd 0x12345678\n") == b"\x78\x56\x34\x12"

    def test_dq_little_endian(self):
        assert assemble("dq 1\n") == b"\x01\x00\x00\x00\x00\x00\x00\x00"

    def test_resb_zero_filled(self):
        assert assemble("resb 4\n") == b"\x00\x00\x00\x00"

    def test_resb_count(self):
        assert len(assemble("resb 10\n")) == 10

    def test_resw_zero_filled(self):
        assert assemble("resw 2\n") == b"\x00\x00\x00\x00"

    def test_resd_zero_filled(self):
        assert assemble("resd 1\n") == b"\x00\x00\x00\x00"

    def test_resq_zero_filled(self):
        assert assemble("resq 1\n") == b"\x00" * 8

    def test_data_after_code(self):
        assert assemble("nop\ndb 0x41\n") == b"\x90\x41"

    def test_hello_string_in_output(self):
        result = assemble('db "hello world", 0x0A\n')
        assert result == b"hello world\x0A"


# ════════════════════════════════════════════════════════════
# 21 — full programs
# ════════════════════════════════════════════════════════════

class TestFullPrograms:

    def test_empty_program(self):
        assert assemble("") == b""

    def test_labels_produce_no_bytes(self):
        assert assemble("_start:\nend:\n") == b""

    def test_comments_produce_no_bytes(self):
        assert assemble("; comment\n") == b""

    def test_loop_ends_with_ret(self):
        source = """
bits 64
    mov  ecx, 10
loop:
    dec  ecx
    jnz  loop
    ret
"""
        result = assemble(source)
        assert result[-1] == 0xC3

    def test_hello_world_contains_string(self):
        source = """
bits 64
_start:
    mov  rax, 1
    mov  rdi, 1
    syscall
    mov  rax, 60
    xor  rdi, rdi
    syscall
msg:
    db "hello", 0x0A
"""
        result = assemble(source)
        assert b"hello" in result

    def test_xor_zeroing_no_null_bytes(self):
        # classic shellcode pattern
        source = """
bits 64
    xor  rax, rax
    xor  rdi, rdi
    xor  rsi, rsi
    xor  rdx, rdx
    mov  al, 0x3b
    syscall
"""
        result = assemble(source)
        # xor instructions produce no null bytes
        assert b"\x00" not in result[:12]

    def test_function_prologue_epilogue(self):
        source = """
bits 64
func:
    push rbp
    mov  rbp, rsp
    sub  rsp, 32
    pop  rbp
    ret
"""
        result = assemble(source)
        assert result[0]  == 0x55    # push rbp
        assert result[-1] == 0xC3    # ret


# ════════════════════════════════════════════════════════════
# 22 — error handling
# ════════════════════════════════════════════════════════════

class TestErrors:

    def test_unsupported_mnemonic_raises(self):
        with pytest.raises(EncoderError):
            assemble("fakeinstr eax\n")

    def test_encoded_instruction_over_15_raises(self):
        enc = EncodedInstruction()
        enc.opcode    = b"\x90" * 14
        enc.immediate = b"\x00\x00"
        with pytest.raises(EncoderError, match="15 byte"):
            enc.to_bytes()

    def test_invalid_sib_scale_raises(self):
        with pytest.raises(EncoderError):
            encode_sib(3, 0, 0)

    def test_invalid_displacement_size_raises(self):
        with pytest.raises(EncoderError):
            encode_displacement(0, 2)

    def test_invalid_immediate_size_raises(self):
        with pytest.raises(EncoderError):
            encode_immediate(0, 3)
