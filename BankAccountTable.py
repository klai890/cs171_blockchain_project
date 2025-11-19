# Class for a bank account table
class BankAccountTable:
    def __init__(self):
        self.table = [100] * 5

    # Retrieve balance of a given client_id
    def get(self, id):
        return self.table[id]
    
    # Update balances after a transaction
    def update(self, sender_id, receiver_id, amount):
        sender_idx = self.ids.index(sender_id)
        receiver_idx = self.ids.index(receiver_id)
        self.table[sender_idx] -= amount
        self.table[receiver_idx] += amount
