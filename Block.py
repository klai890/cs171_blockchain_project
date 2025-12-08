import string
import random
import hashlib

# Class for a single block
class Block:
    def __init__(self, sender_id, receiver_id, amount, prev_hash, hash_pointer=None, nonce=None):
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount
        self.prev_hash = prev_hash

        self.nonce = nonce if nonce else None
        self.hash_pointer = hash_pointer if hash_pointer else self.calculate_hash()

    def calculate_hash(self):
        # if self.nonce is None:
        #     raise ValueError("Nonce needs to be set before calculating hash pointer")

        txns = f"{self.sender_id},{self.receiver_id},{self.amount}"
        content = f"{txns}{self.nonce}{self.prev_hash}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def calculate_nonce(self):
        possible_chars = string.ascii_letters + string.digits
        
        while True:
            nonce = ''.join(random.choice(possible_chars) for _ in range(16))
            txns = f"{self.sender_id},{self.receiver_id},{self.amount}"
            
            # Concatenate txns and nonce, convert to bytes, use SHA256 to hash, convert hash to hexadecimal
            hash_bytes = hashlib.sha256(f"{txns}{nonce}".encode('utf-8'))
            hash_res = hash_bytes.hexdigest()
            if hash_res[-1] in ['0', '1', '2', '3', '4']:
                print(f"Valid nonce found --> nonce: {nonce}, hash: {hash_res}")
                break

        self.nonce = nonce

    def __eq__(self, other):
        return (self.sender_id == other.sender_id and
                self.receiver_id == other.receiver_id and
                self.amount == other.amount and
                self.prev_hash == other.prev_hash and
                self.nonce == other.nonce and
                self.hash_pointer == other.hash_pointer)

    def to_dict(self):
        return {
            "sender": self.sender_id,
            "receiver": self.receiver_id,
            "amount": self.amount,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
            "hash_pointer": self.hash_pointer
        }
    
    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
        return cls(data["sender"], data["receiver"], data["amount"], data["prev_hash"], data["hash_pointer"], data["nonce"])

    def __str__(self):
        return f"Block(sender: {self.sender_id}, receiver: {self.receiver_id}, amount: {self.amount}, hash: {self.hash_pointer}, nonce: {self.nonce})"