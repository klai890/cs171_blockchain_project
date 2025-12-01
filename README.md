# CS 171 Blockchain Project

## Configuration Details

Specify the host and ports in `config.yaml`. 

Processes have IDs $0, 1, 2, ..., n-1$ if there are $n$ ports, and the $i$-th process is assigned to $\text{ports}[i]$

## Tests

1. Test that `PROMISE` works correctly (that a node that has `PROMISE`-ed a greater ballot does not send a promise to a smaller ballot).

Question: In our current implemenentation, once a process receive `PROMISE` from a majority, it will send `ACCEPT` messages to ONLY that majority. Eg: A process receives 5 `PROMISE`, but only sends `ACCEPT` to 3 of them. What's the expected behavior if one of the three fail? That is, should we be sending `ACCEPT` to all processes that we receive `PROMISE` for (wait for all 5)? If so, is there a set amount of time we should wait for?

- If there's a set amount of time: We know delays are 3 seconds so we can use that to calculate the amount of wait time so that we know that if a process hasn't replied by then, it's crashed.

## Todos

- [ ] Need to develop a good suite of test cases (that consider edge cases, crash failure situations, concurrent events)
- [ ] Need to implement persist to disk & process crash failure recovery
- [ ] Need to handle leader failures