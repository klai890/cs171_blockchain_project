# CS 171 Blockchain Project

## Configuration Details

Specify the host and ports in `config.yaml`. 

Processes have IDs $0, 1, 2, ..., n-1$ if there are $n$ ports, and the $i$-th process is assigned to $\text{ports}[i]$

## Tests

1. Test that `PROMISE` works correctly (that a node that has `PROMISE`-ed a greater ballot does not send a promise to a smaller ballot).

## Stuff that needs work

1. Updating depth and sequence number for PAXOS
2. Logic to update the blockchain (Blockchain.add_block)
3. Hash logic (previous_hash in Process.begin)
4. In general – need to think of edge cases / good test cases.