# 
# NOTE: order should be like this : 
# Legacy Prefix | REX | Opcode | ModRM | SIB | Displacement | Immediate 
# 
 
class Operand: 
    def __init__(self, name:str):
        self.name = name
        print(self.name)

class EncodingInstructions: 
    def __init__(self, name:str):
        self.name = name
        print(self.name)






