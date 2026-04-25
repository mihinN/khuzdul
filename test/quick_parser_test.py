from assembler.ir import IRProgram, IRInstruction, IRLabel
from assembler.ir import Operand, OperandKind, OperandSize
from assembler.ir import EncodingPref, REGISTER_SIZE, OPCODE_TABLE

# check connections
print("EAX size:", REGISTER_SIZE["EAX"])    # 32
print("RAX size:", REGISTER_SIZE["RAX"])    # 64
print("MOV opcodes:", [o.hex() for o in OPCODE_TABLE["MOV"]])

# build small program
p = IRProgram()
p.constraints.forbidden_bytes = {0x00, 0x0a, 0x0d}
p.constraints.pic_mode        = True

p.add(IRLabel("_start", line=1))

instr = IRInstruction("MOV", line=2)
instr.operands.append(Operand(OperandKind.REGISTER,  "EAX", OperandSize.DWORD))
instr.operands.append(Operand(OperandKind.IMMEDIATE,  1,    OperandSize.DWORD))
instr.enc_pref = EncodingPref.AVOID_NULL
p.add(instr)

p.add(IRInstruction("SYSCALL", line=3))
p.dump()
