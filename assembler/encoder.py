# 
# NOTE: order should be like this : 
# Legacy Prefix | REX | Opcode | ModRM | SIB | Displacement | Immediate 
# 
 
import struct
from assembler.ir import (IRData, IRDirectives, IRInstructions, IRLabel, IRProgram, Instructions, Operand, OperandSize, OperandType, EncodingPref)
from assembler.symbol_table import SymbolTable
from assembler.error import EncoderError

