# Class for a bank account table
class BankAccountTable:
    def __init__(self):
        self.table = {i: 100 for i in range(5)}  # should this go from 0-4 or 1-5? also changed this to a dictionary, not sure if we should change it back to a list
        self.filename = "block_contents.json"

    # Retrieve balance of a given client_id
    def get(self, id):
        return self.table[id]
    
    # Update balances after a transaction
    def update(self, sender_id, receiver_id, amount):
        if self.table[int(sender_id)] >= amount:
            # sender_idx = self.ids.index(sender_id)
            # receiver_idx = self.ids.index(receiver_id)
            self.table[int(sender_id)] -= amount
            self.table[int(receiver_id)] += amount
