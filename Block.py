# Class for a single block
class Block:
    def __init__(self, sender_id, receiver_id, amount):
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount
        self.hash_pointer = None
        self.nonce = None

    def calculate_hash(self):
        pass

    def calculate_nonce(self):
        pass

    def __str__(self):
        return f"Block(sender: {self.sender_id}, receiver: {self.receiver_id}, amount: {self.amount}, nonce: {self.nonce})"