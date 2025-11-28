class Ballot:
    def __init__(self, seq_num, pid, depth):
        self.seq_num = seq_num
        self.pid = pid
        self.depth = depth

    # Compare 2 ballots
    def __gt__(self, other):
        if not isinstance(other, Ballot):
            raise TypeError
        
        if self.seq_num > other.seq_num:
            return True
        
        if self.seq_num == other.seq_num and self.pid > other.pid:
            return True
        
        return False
    
    def __eq__(self, other):
        if not isinstance(other, Ballot):
            raise TypeError
        
        return self.seq_num == other.seq_num and self.pid == other.pid and self.depth == other.depth
    
    def __str__(self):
        return f"({self.seq_num}, {self.pid}, {self.depth})"

    def to_dict(self):
        return {
            "seq_num": self.seq_num,
            "pid": self.pid,
            "depth": self.depth
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(data["seq_num"], data["pid"], data["depth"])