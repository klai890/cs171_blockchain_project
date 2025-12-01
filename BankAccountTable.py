# Class for a bank account table
class BankAccountTable:
    def __init__(self):
        self.table = [100] * 5
        self.filename = "block_contents.json"

    # Retrieve balance of a given client_id
    def get(self, id):
        if id not in range(5):
            raise RuntimeError(f"BankAccountTable: {id} out of range")
        return self.table[id]
    
    # Update balances after a transaction
    def update(self, sender_id, receiver_id, amount):
        if sender_id not in range(5) or receiver_id not in range(5):
            raise RuntimeError(f"BankAccountTable: {id} out of range")
        
        if self.table[int(sender_id)] >= amount:
            self.table[int(sender_id)] -= amount
            self.table[int(receiver_id)] += amount

    def __str__(self):
        res = ""
        for i in range(5):
            res += f"Process {i}: {self.table[i]}\n"
        return res