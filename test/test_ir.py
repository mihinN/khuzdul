# test/test_ir.py
from assembler.ir import (
    IRProgram, IRInstructions, IRLabel, IRDirectives, IRData,
    Operand, OperandType, OperandSize, EncodingPref,
    ShellcodeConstraints, REGISTER_SIZE, OPCODE_TABLE
)


# ── ISA Tables ────────────────────────────────────────────────────

def test_register_size_8bit():
    assert REGISTER_SIZE["AL"]  == OperandSize.BYTE
    assert REGISTER_SIZE["AH"]  == OperandSize.BYTE
    assert REGISTER_SIZE["BL"]  == OperandSize.BYTE

def test_register_size_16bit():
    assert REGISTER_SIZE["AX"]  == OperandSize.WORD
    assert REGISTER_SIZE["BX"]  == OperandSize.WORD
    assert REGISTER_SIZE["CS"]  == OperandSize.WORD   # segment
    assert REGISTER_SIZE["IP"]  == OperandSize.WORD   # IP_16

def test_register_size_32bit():
    assert REGISTER_SIZE["EAX"] == OperandSize.DWORD
    assert REGISTER_SIZE["EBX"] == OperandSize.DWORD
    assert REGISTER_SIZE["EIP"] == OperandSize.DWORD

def test_register_size_64bit():
    assert REGISTER_SIZE["RAX"] == OperandSize.QWORD
    assert REGISTER_SIZE["RBX"] == OperandSize.QWORD
    assert REGISTER_SIZE["RIP"] == OperandSize.QWORD
    assert REGISTER_SIZE["CR0"] == OperandSize.QWORD
    assert REGISTER_SIZE["DR0"] == OperandSize.QWORD

def test_register_size_simd():
    assert REGISTER_SIZE["MMX0"] == OperandSize.QWORD
    assert REGISTER_SIZE["K0"]   == OperandSize.QWORD
    assert REGISTER_SIZE["MXCSR"] == OperandSize.DWORD

def test_register_size_flags():
    assert REGISTER_SIZE["ZF"] == OperandSize.NONE
    assert REGISTER_SIZE["CF"] == OperandSize.NONE

def test_register_size_elb():
    assert REGISTER_SIZE["SIL"] == OperandSize.BYTE
    assert REGISTER_SIZE["R8B"] == OperandSize.BYTE

def test_opcode_table_mov():
    assert "MOV" in OPCODE_TABLE
    assert len(OPCODE_TABLE["MOV"]) > 0

def test_opcode_table_add():
    assert "ADD" in OPCODE_TABLE

def test_opcode_table_nop():
    assert "NOP" in OPCODE_TABLE
    assert b"\x90" in OPCODE_TABLE["NOP"]

def test_opcode_table_hlt():
    assert "HLT" in OPCODE_TABLE
    assert b"\xF4" in OPCODE_TABLE["HLT"]

def test_opcode_table_unknown():
    assert OPCODE_TABLE.get("FAKEINSTR", []) == []


# ── Operand ───────────────────────────────────────────────────────

def test_operand_register():
    op = Operand(OperandType.REGISTER, "EAX", OperandSize.DWORD)
    assert op.op_type == OperandType.REGISTER
    assert op.value   == "EAX"
    assert op.size    == OperandSize.DWORD

def test_operand_immediate():
    op = Operand(OperandType.IMMEDIATE, 42, OperandSize.DWORD)
    assert op.op_type == OperandType.IMMEDIATE
    assert op.value   == 42

def test_operand_memory_defaults():
    op = Operand(OperandType.MEMORY, None)
    assert op.base            == None
    assert op.index           == None
    assert op.scale           == 1
    assert op.disp            == 0
    assert op.is_rip_relative == False

def test_operand_memory_fields():
    op        = Operand(OperandType.MEMORY, None, OperandSize.DWORD)
    op.base   = "EBX"
    op.index  = "ESI"
    op.scale  = 4
    op.disp   = 8
    assert op.base  == "EBX"
    assert op.index == "ESI"
    assert op.scale == 4
    assert op.disp  == 8

def test_operand_rip_relative():
    op                 = Operand(OperandType.MEMORY, None)
    op.base            = "RIP"
    op.disp            = 16
    op.is_rip_relative = True
    assert op.is_rip_relative == True
    assert op.base             == "RIP"

def test_operand_label_ref():
    op = Operand(OperandType.LABEL_REF, "main")
    assert op.op_type == OperandType.LABEL_REF
    assert op.value   == "main"

def test_operand_default_size():
    op = Operand(OperandType.REGISTER, "EAX")
    assert op.size == OperandSize.NONE

def test_operand_repr():
    op  = Operand(OperandType.REGISTER, "EAX", OperandSize.DWORD)
    rep = repr(op)
    assert "REGISTER" in rep
    assert "EAX"      in rep


# ── IRInstructions ────────────────────────────────────────────────

def test_irinstructions_basic():
    instr = IRInstructions("MOV")
    assert instr.mnemonic  == "MOV"
    assert instr.operands  == []
    assert instr.line      == 0
    assert instr.column    == 0

def test_irinstructions_opcodes_loaded():
    instr = IRInstructions("MOV")
    assert len(instr.opcode) > 0

def test_irinstructions_unknown_mnemonic():
    instr = IRInstructions("FAKEINSTR")
    assert instr.opcode == []

def test_irinstructions_defaults():
    instr = IRInstructions("ADD")
    assert instr.pic_good              == False
    assert instr.uses_abs              == False
    assert instr.enc_pref              == EncodingPref.DEFAULT
    assert instr.enc_bytes             == None
    assert instr.forbidden             == set()
    assert instr.satisfies_constraints == True

def test_irinstructions_with_operands():
    op1   = Operand(OperandType.REGISTER,  "EAX", OperandSize.DWORD)
    op2   = Operand(OperandType.IMMEDIATE,  1,    OperandSize.DWORD)
    instr = IRInstructions("MOV", operands=[op1, op2], line=5, column=4)
    assert len(instr.operands) == 2
    assert instr.line          == 5
    assert instr.column        == 4

def test_irinstructions_encoding_pref():
    instr          = IRInstructions("XOR")
    instr.enc_pref = EncodingPref.AVOID_NULL
    assert instr.enc_pref == EncodingPref.AVOID_NULL

def test_irinstructions_pic_flag():
    instr          = IRInstructions("JMP")
    instr.pic_good = True
    assert instr.pic_good == True

def test_irinstructions_repr():
    instr = IRInstructions("MOV")
    rep   = repr(instr)
    assert "MOV" in rep


# ── IRLabel ───────────────────────────────────────────────────────

def test_irlabel_global():
    label = IRLabel("main", line=1, column=0)
    assert label.name     == "main"
    assert label.is_local == False
    assert label.offset   == None

def test_irlabel_local():
    label = IRLabel(".loop", line=3)
    assert label.name     == ".loop"
    assert label.is_local == True

def test_irlabel_local_done():
    label = IRLabel(".done")
    assert label.is_local == True

def test_irlabel_start():
    label = IRLabel("_start")
    assert label.is_local == False

def test_irlabel_offset_filled():
    label        = IRLabel("main")
    label.offset = 0x10
    assert label.offset == 0x10

def test_irlabel_repr():
    label = IRLabel("main")
    rep   = repr(label)
    assert "main"  in rep
    assert "local" in rep


# ── IRDirectives ──────────────────────────────────────────────────

def test_irdirectives_basic():
    d = IRDirectives("SECTION", args=[".text"])
    assert d.name == "SECTION"
    assert d.args == [".text"]

def test_irdirectives_no_args():
    d = IRDirectives("GLOBAL")
    assert d.args == []

def test_irdirectives_repr():
    d   = IRDirectives("SECTION", [".data"])
    rep = repr(d)
    assert "SECTION" in rep


# ── IRData ────────────────────────────────────────────────────────

def test_irdata_basic():
    d = IRData("msg", OperandSize.BYTE, values=["hello", 0])
    assert d.label  == "msg"
    assert d.size   == OperandSize.BYTE
    assert d.values == ["hello", 0]

def test_irdata_no_label():
    d = IRData(None, OperandSize.DWORD)
    assert d.label  == None
    assert d.values == []

def test_irdata_repr():
    d   = IRData("msg", OperandSize.BYTE, ["hello"])
    rep = repr(d)
    assert "msg" in rep


# ── ShellcodeConstraints ──────────────────────────────────────────

def test_constraints_defaults():
    c = ShellcodeConstraints()
    assert c.forbidden_bytes == set()
    assert c.max_size        == 0
    assert c.pic_mode        == False
    assert c.encoding_pref   == EncodingPref.DEFAULT

def test_constraints_add_badchar():
    c = ShellcodeConstraints()
    c.add_badchar(0x00)
    c.add_badchar(0x0a)
    assert 0x00 in c.forbidden_bytes
    assert 0x0a in c.forbidden_bytes

def test_constraints_is_byte_ok():
    c = ShellcodeConstraints()
    c.add_badchar(0x00)
    assert c.is_byte_ok(0x00) == False
    assert c.is_byte_ok(0x90) == True

def test_constraints_check_bytes_clean():
    c          = ShellcodeConstraints()
    c.forbidden_bytes = {0x00}
    violations = c.check_bytes(b"\x90\x90\x90")
    assert violations == []

def test_constraints_check_bytes_violation():
    c          = ShellcodeConstraints()
    c.forbidden_bytes = {0x00}
    violations = c.check_bytes(b"\x90\x00\x90")
    assert len(violations)   == 1
    assert violations[0][0]  == 1      # offset
    assert violations[0][1]  == 0x00   # byte

def test_constraints_multiple_violations():
    c          = ShellcodeConstraints()
    c.forbidden_bytes = {0x00, 0x0a}
    violations = c.check_bytes(b"\x00\x90\x0a")
    assert len(violations) == 2

def test_constraints_repr():
    c   = ShellcodeConstraints()
    rep = repr(c)
    assert "ShellcodeConstraints" in rep


# ── IRProgram ─────────────────────────────────────────────────────

def test_irprogram_empty():
    p = IRProgram()
    assert p.nodes       == []
    assert p.symbols     == {}
    assert isinstance(p.constraints, ShellcodeConstraints)

def test_irprogram_add_instruction():
    p     = IRProgram()
    instr = IRInstructions("MOV")
    p.add(instr)
    assert len(p.nodes)        == 1
    assert len(p.instructions()) == 1

def test_irprogram_add_label():
    p     = IRProgram()
    label = IRLabel("main")
    p.add(label)
    assert len(p.labels()) == 1

def test_irprogram_add_directive():
    p = IRProgram()
    p.add(IRDirectives("SECTION", [".text"]))
    assert len(p.directives()) == 1

def test_irprogram_add_data():
    p = IRProgram()
    p.add(IRData("msg", OperandSize.BYTE, ["hello"]))
    assert len(p.data()) == 1

def test_irprogram_mixed_nodes():
    p = IRProgram()
    p.add(IRLabel("_start"))
    p.add(IRInstructions("MOV"))
    p.add(IRInstructions("SYSCALL"))
    p.add(IRDirectives("SECTION", [".text"]))
    assert len(p.instructions()) == 2
    assert len(p.labels())       == 1
    assert len(p.directives())   == 1

def test_irprogram_symbols():
    p            = IRProgram()
    p.symbols["main"] = 0x00
    p.symbols["loop"] = 0x10
    assert p.symbols["main"] == 0x00
    assert p.symbols["loop"] == 0x10

def test_irprogram_constraints():
    p = IRProgram()
    p.constraints.add_badchar(0x00)
    p.constraints.pic_mode  = True
    p.constraints.max_size  = 64
    assert 0x00              in p.constraints.forbidden_bytes
    assert p.constraints.pic_mode  == True
    assert p.constraints.max_size  == 64

def test_irprogram_dump_runs():
    # just check dump doesnt crash
    p = IRProgram()
    p.add(IRLabel("_start", line=1))
    instr          = IRInstructions("MOV", line=2)
    instr.operands = [
        Operand(OperandType.REGISTER,  "EAX", OperandSize.DWORD),
        Operand(OperandType.IMMEDIATE,  1,    OperandSize.DWORD),
    ]
    p.add(instr)
    p.add(IRDirectives("SECTION", [".text"]))
    p.add(IRData("msg", OperandSize.BYTE, ["hello"]))
    p.dump()   # should not raise
