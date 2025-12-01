from Block import Block

# Class for the blockchain
class Blockchain:
    def __init__(self):
        self.chain = []

    def get_last(self):
        if len(self.chain) == 0:
            return None
        
        else:
            return self.chain[-1].hash_pointer

    def add_block(self, block):
        self.chain.append(block)
    
    def get_depth(self):
        return len(self.chain)

    def __str__(self):
        chain_str = ""
        for block in self.chain:
            chain_str += str(block) + "\n"
        return chain_str