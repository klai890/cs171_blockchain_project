import string
import random
import hashlib

# Class for a single block
class Block:
    def __init__(self, sender_id, receiver_id, amount, prev_hash):
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount
        self.prev_hash = prev_hash

        # *** A little confused here... I think I might be mixing up previous vs. current when calculating nonce and hash pointer ***
        self.nonce = self.calculate_nonce()
        self.hash_pointer = self.calculate_hash()

    def calculate_hash(self):
        txns = f"{self.sender_id},{self.receiver_id},{self.amount}"
        content = f"{txns}{self.nonce}{self.prev_hash}"
        hash_res = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return hash_res

    def calculate_nonce(self):
        possible_chars = string.ascii_letters + string.digits
        
        while True:
            nonce = ''.join(random.choice(possible_chars) for _ in range(16))
            txns = f"{self.sender_id},{self.receiver_id},{self.amount}" # replace with str(self)?
            
            # Concatenate txns and nonce, convert to bytes, use SHA256 to hash, convert hash to hexadecimal
            hash_bytes = hashlib.sha256(f"{txns}{nonce}".encode('utf-8'))
            hash_res = hash_bytes.hexdigest()
            if hash_res[-1] in ['0', '1', '2', '3', '4']:
                print(f"Valid nonce found --> nonce: {nonce}, hash: {hash_res}")
                return nonce

    def __str__(self):
        return f"Block(sender: {self.sender_id}, receiver: {self.receiver_id}, amount: {self.amount}, nonce: {self.nonce})"