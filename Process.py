import re
import sys
import json
import yaml
import os
from BankAccountTable import BankAccountTable
from Blockchain import Blockchain
from Block import Block
from Ballot import Ballot
import asyncio
from asyncio import as_completed, create_task

# Class for a single process
class Process:
    # Constructor to initialize process attributes

    '''
    __init__
        - process_id: The id of this process
        - host: The host
        - ports: The ports of all processes, where ports[i] represents the port of process_id i
    '''
    def __init__(self, process_id, host, ports):
        self.process_id = process_id
        self.host = host
        self.ports = ports
        self.num_processes = len(ports)
        self.port_number = ports[process_id]

        print(f"{self.host=}")
        print(f"{self.ports=}")
        print(f"{self.ports=}")

        # Data
        self.bank_account_table = BankAccountTable()
        self.blockchain = Blockchain()

        # Paxos states
        self.sequence_no = 0
        self.accept_val = None # type Block
        self.accept_num = Ballot(-1,-1,0)
        self.highest_promise = Ballot(-1,-1,0)
        
        # Node states
        self.alive = True
        self.is_leader = False
        self.promises = 0
        self.accepts = 0

    '''
    Server handling
    '''

    # Establish server
    async def start_server(self):
        print(f"Process {self.process_id} starting server at port {self.port_number}...")
        # Set up server socket to listen for incoming messages
        # Handle incoming messages in a separate thread

        server = await asyncio.start_server(self.handle_conn, self.host, self.port_number)
        async with server:
            await server.serve_forever()

    # Handle incoming connections
    async def handle_conn(self, reader, writer):
        data = await reader.read(1024)
        if not data:
            writer.close()
            await writer.wait_closed()
            return
        
        await self.parse_data(data, writer)
        await writer.drain()

        writer.close()
        await writer.wait_closed()

    # Handle incoming messages from potential leaders
    async def parse_data(self, data, writer):
        if data:
            msg = json.loads(data.decode())
            type = msg.get('type')

            print(f"Received message {type} from process ID {msg.get('id')}")

            if type == 'QUERY_DEPTH':
                response = {
                    "id": self.process_id,
                    "type": "DEPTH_RESPONSE",
                    "depth": self.blockchain.get_depth()
                }

                writer.write(json.dumps(response).encode())
                return
        
            if type == 'REQUEST_BLOCKCHAIN':
                response = {
                    "id": self.process_id,
                    "type": "BLOCKCHAIN_RESPONSE",
                    "blockchain": [block.to_dict() for block in self.blockchain.chain]
                }

                writer.write(json.dumps(response).encode())
                return

            # Ignore messages if process is failed
            if not self.alive:
                print("Process is failed, ignoring message")
                # Still send a response so sender doesn't hang
                response = {"id": self.process_id, "type": "FAILED"}
                writer.write(json.dumps(response).encode())
                return

            # Check message type
            if type == 'PREPARE':
                print("Processing PREPARE message...")
                proposer_ballot = Ballot.from_dict(msg.get('ballot'))
                respond = True
                
                print(f"Process {self.process_id} blockchain depth: {self.blockchain.get_depth()}, Proposer depth: {proposer_ballot.depth}")
                print(f"Process {self.process_id} highest promise: {self.highest_promise}")

                # Acceptor does not accept prepare or accept messages from a contending leader if the depth 
                # of the block being proposed is lower than the acceptor’s depth of its copy of the blockchain
                if proposer_ballot.depth < self.blockchain.get_depth():
                    print(f"Witholding Response: Proposer ballot has depth {proposer_ballot.depth}; depth {self.blockchain.get_depth()}")
                    respond = False

                # If we already sent promise to a proposer w/ higher ballot => ignore
                if self.highest_promise.depth == proposer_ballot.depth and self.highest_promise > proposer_ballot:
                    print(f"Witholding Response: Highest promise sent was to {self.highest_promise}, proposer ballot is {proposer_ballot}")
                    respond = False

                # Otherwise, reply with PROMISE
                if respond:
                    self.highest_promise = proposer_ballot
                    send_ballot = self.accept_num if (self.accept_num and self.accept_num.depth == proposer_ballot.depth) else proposer_ballot
                    msg = {
                        "id": self.process_id, 
                        "type": "PROMISE", 
                        "value": self.accept_val.to_dict() if (self.accept_val and self.accept_num.depth == proposer_ballot.depth) else None, # can be None or a Block
                        "ballot": send_ballot.to_dict() # proposer's ballot if no prev accepted value
                    }

                    print("Sending message", msg)
                    writer.write(json.dumps(msg).encode())

            elif type == 'ACCEPT':
                print("Processing ACCEPT message...")
                proposer_ballot = Ballot.from_dict(msg.get("ballot"))
                block = Block.from_dict(msg.get("value"))

                respond = True

                # An acceptor does not accept prepare or accept messages from a contending leader if the depth 
                # of the block being proposed is lower than the acceptor’s depth of its copy of the blockchain
                if proposer_ballot.depth < self.blockchain.get_depth():
                    print(f"Witholding Response: Proposer ballot has depth {proposer_ballot.depth}; depth {self.blockchain.get_depth()}")
                    respond = False

                if self.highest_promise.depth != proposer_ballot.depth or self.highest_promise != proposer_ballot:
                    print(f"Witholding Response: Highest promise sent was to {self.highest_promise}, proposer ballot is {proposer_ballot}")
                    respond = False

                if respond:
                    self.accept_num = proposer_ballot
                    self.accept_val = block
                    msg = {
                        "id": self.process_id,
                        "type": "ACCEPTED",
                        "value": block.to_dict(),
                        "ballot": proposer_ballot.to_dict()
                    }
                    print("Sending message", msg)
                    writer.write(json.dumps(msg).encode())


            elif type == 'DECIDE':
                block = Block.from_dict(msg.get('value'))
                sender = msg.get('sender')
                receiver = msg.get('receiver')
                amount = msg.get('amount')

                self.blockchain.add_block(block)
                self.bank_account_table.update(sender, receiver, amount)

                self.save_state_to_disk()

                # Reinitialize seq_num, accept_val, accept_num for each new block added
                self.sequence_no = 0
                self.accept_num = Ballot(-1,-1, self.blockchain.get_depth())
                self.accept_val = None
                self.highest_promise = Ballot(-1,-1, self.blockchain.get_depth())

    '''
    Handle user input
    '''
    # Handle input from the user.
    async def handle_user(self):

        while True:
            user_input = await asyncio.get_event_loop().run_in_executor(None, input)
            user_input = user_input.strip()

            # Check valid user input
            pattern = r"^moneyTransfer\(\s*([0-4])\s*,\s*([0-4])\s*,\s*(\d+(?:\.\d+)?)\s*\)$"
            match = re.match(pattern, user_input)

            if match:
                print("Valid moneyTransfer command received...")
                debit_node = int(match.group(1))
                credit_node = int(match.group(2))
                amount = float(match.group(3))

                # Check that debit_node has sufficient funds
                if self.bank_account_table.get(debit_node) >= amount and amount > 0:
                    print(f"Processing transaction from Node {debit_node} to Node {credit_node} for amount {amount}...")
                    asyncio.create_task(self.begin(debit_node, credit_node, amount))

                else:
                    print(f"Node {debit_node} has insufficient funds for transaction.")
                
            # Failed process: Should not send or receive any messages (or respond to user input??)
            elif user_input == "failProcess":
                self.alive = False

            # Restart process: Resume sending and receiving messages
            elif user_input == "fixProcess":
                if self.alive == False:
                    self.alive = True
                    await self.restore()

            elif user_input == "printBlockchain":
                print(self.blockchain)

            elif user_input == "printBalance":
                print(self.bank_account_table)

            else:
                print("Invalid user command was entered. Valid commands include:\n- moneyTransfer(debit_node, credit_node, amount), where debit_node and credit_node are 0-4 and amount is a positive number\n- failProcess\n- fixProcess\n- printBlockchain\n- printBalance\n")
    
    '''
    Helper functions
    '''

    # Sends a message to other clients
    async def send_to_client(self, client_id, msg, wait_for_reply=True):
        if self.alive == False:
            print(f"Process {self.process_id} is failed, cannot send message to Client {client_id}")
            return None
        
        print(f"Sending {msg.get('type').upper()} to Client {client_id}")
        try:
            reader, writer = await asyncio.open_connection(self.host, self.ports[client_id])

            # Send message
            writer.write(json.dumps(msg).encode())
            await writer.drain()

            # Wait for reply 
            if wait_for_reply:
                data = await reader.read(1024)
                reply = json.loads(data.decode()) if data else None
            
                # Simulate 3 second delay (3 sec from other client to this client)
                await asyncio.sleep(3)

                writer.close()
                await writer.wait_closed()
                return reply
            else:
                writer.close()
                await writer.wait_closed()
                return None
        
        except TimeoutError:
            print(f"Timeout while waiting for Client {client_id}'s response.")
            return None

        except ConnectionRefusedError:
            print(f"Connection to Client {client_id} refused.")
            return None

    # Retrieve a list of other pids
    def get_other_clients(self):
        return [i for i in range(5) if i != self.process_id]

    '''
    PAXOS functions
    '''

    # First, PREPARE. If successful, PROPOSE. If successful, ACCEPT. If successful, DECIDE.
    async def begin(self, sender, receiver, amount):
        # Tracks the attempts the leader makes to get majority -- when proposal fails, increment sequence_no and retry
        leader_attempts = 0

        while leader_attempts < 5: 
            if not self.alive:
                print(f"Process {self.process_id} failed")
                return
            
            ballot = Ballot(self.sequence_no, self.process_id, self.blockchain.get_depth())
            print(f"Attempt: {leader_attempts + 1}, Starting Ballot: {ballot}")

            promises = await self.start_election(ballot)
            print(f"Received {len(promises)} promises: {promises}")

            if not self.alive:
                print(f"Process {self.process_id} failed")
                return
            
            # Did not receive a majority.
            if len(promises) <= self.num_processes / 2:
                print("Failed to get majority, leader retrying")
                self.sequence_no += 1
                leader_attempts += 1
                await asyncio.sleep(0.5)  # small delay before retrying
                continue

            # Process PROMISES to select a block to propose.
            block_to_propose = None

            # See if there is already an accepted block for this depth
            non_bottoms = [item for item in promises if item['value'] != None and Ballot.from_dict(item['ballot']).depth == self.blockchain.get_depth()]
            
            # Select value with the highest process ID
            if len(non_bottoms) != 0:
                block_to_propose = max(non_bottoms, key=lambda x: Ballot.from_dict(x['ballot']))
                block_to_propose = Block.from_dict(block_to_propose['value'])
                print("Block to propose:", block_to_propose)

            # Otherwise, we must create a new Block (mining)
            else:
                if not self.alive:
                    print(f"Process {self.process_id} failed before mining")
                    return
            
                prev_hash =  self.blockchain.get_last()
                block_to_propose = Block(sender, receiver, amount, prev_hash)
                block_to_propose.calculate_nonce()

                if not self.alive:
                    print(f"Process {self.process_id} failed after mining")
                    return

            # Propose block
            accepteds = await self.propose(ballot, block_to_propose)

            if not self.alive:
                print(f"Process {self.process_id} failed")
                return
            
            # Did not receive ACCEPTED from majority
            if len(accepteds) <= self.num_processes / 2:
                print("Did not receive ACCEPTED from majority, retrying with higher ballot")
                self.sequence_no += 1
                leader_attempts += 1
                await asyncio.sleep(0.5)
                continue
            
            # Otherwise, send decision to all nodes
            print(f"Consensus reached with {ballot}!")
            await self.decide(block_to_propose, sender, receiver, amount)
            return

        print(f"Consensus couldn't be reached with {ballot}...")

    # This process attempts to become leader
    async def start_election(self, ballot):
        # Send PREPARE to all other clients
        other_clients = self.get_other_clients()
        msg = {"id": self.process_id, "type": "PREPARE", "ballot": ballot.to_dict()} 

        # Await PROMISE from majority
        tasks = [create_task(self.send_to_client(cid, msg, True)) for cid in other_clients]
        replies = []

        # Proposer implicitly accepts its own ballot
        if self.highest_promise < ballot or self.highest_promise.depth < ballot.depth:
            self.highest_promise = ballot
            replies.append({
                    "id": self.process_id, 
                    "type": "PROMISE", 
                    "value": None,
                    "ballot": ballot.to_dict()
            })

        for completed_task in as_completed(tasks):
            reply = await completed_task
            if reply and reply.get('type') == 'PROMISE':
                replies.append(reply)

            # Majority
            if len(replies) > self.num_processes / 2:
                break

        # Received PROMISE from majority.
        return replies


    # This process believes it is leader, has successfully mined => Proposes a value.
    async def propose(self, ballot, block_to_propose):
        print("Starting proposal...")

        # Send ACCEPT messages
        other_clients = self.get_other_clients()
        msg = {
            "id": self.process_id, 
            "type": "ACCEPT", 
            "ballot": ballot.to_dict(), 
            "value": block_to_propose.to_dict()
        } 

        tasks = [create_task(self.send_to_client(cid, msg, True)) for cid in other_clients]
        replies = []

        # Implicitly accepts its own 
        if self.highest_promise == ballot:
            self.accept_num = ballot
            self.accept_val = block_to_propose
            replies.append({
                "id": self.process_id,
                "type": "ACCEPTED",
                "ballot": ballot.to_dict(),
                "value": block_to_propose.to_dict(),
            })

        for completed_task in as_completed(tasks):
            reply = await completed_task

            # Ensure that ACCEPTED ballot/block match.
            if reply and reply.get('type') == 'ACCEPTED':
                accepted_block = Block.from_dict(reply.get('value'))
                accepted_ballot = Ballot.from_dict(reply.get('ballot'))
                if block_to_propose == accepted_block and ballot == accepted_ballot:
                    replies.append(reply)

            # Majority
            if len(replies) > self.num_processes / 2:
                break

        # Received ACCEPTED from a majority
        return replies

    # This process has received majority accepted values, must decide
    async def decide(self, block, sender, receiver, amount):
        # If majority accepted: Append block to self.blockchain, update self.bank_account_table.
        self.blockchain.add_block(block)
        self.bank_account_table.update(sender, receiver, amount)

        self.save_state_to_disk()

        # Reinitialize seq_num, accept_val, accept_num for each new block added
        self.sequence_no = 0
        self.accept_num = Ballot(-1,-1, self.blockchain.get_depth())
        self.accept_val = None
        self.highest_promise = Ballot(-1,-1, self.blockchain.get_depth())

        # Send DECIDE to all
        other_clients = self.get_other_clients()
        msg = {
            "id": self.process_id, 
            "type": "DECIDE", 
            "value": block.to_dict(),
            "sender": sender,
            "receiver": receiver,
            "amount": amount
        } 
        
        await asyncio.gather(*(self.send_to_client(cid, msg, False) for cid in other_clients))        

    # Return filename for this process's state
    def get_filename(self):
        return f"process_{self.process_id}_state.json"

    # Write blockhain and bank table to disk
    def save_state_to_disk(self):
        state = {
            "blockchain": [block.to_dict() for block in self.blockchain.chain],
            "bank_accounts": self.bank_account_table.table,
            "sequence_no": self.sequence_no,
            "accept_num": self.accept_num.to_dict(),
            "accept_val": self.accept_val.to_dict() if self.accept_val else None,
            "highest_promise": self.highest_promise.to_dict()
        }
        
        filename = self.get_filename()
        temp = filename + ".tmp"
        
        # Write to temp file first, then swap temp with actual file
        with open(temp, 'w') as f:
            json.dump(state, f, indent=2)
        
        os.replace(temp, filename)
        print(f"Process {self.process_id} state saved to disk!")
    
    # Load blockhain and bank table from disk
    def load_state_from_disk(self):
        filename = self.get_filename()
        
        if not os.path.exists(filename):
            print(f"No saved state file found for process {self.process_id}")
            return False
        
        try:
            with open(filename, 'r') as f:
                state = json.load(f)
            
            # Restore blockchain
            self.blockchain.chain = [Block.from_dict(block) for block in state["blockchain"]]
            
            # Restore bank accounts
            self.bank_account_table.table = state["bank_accounts"]
            
            # Restore Paxos state
            self.sequence_no = state["sequence_no"]
            self.accept_num = Ballot.from_dict(state["accept_num"])
            self.accept_val = Block.from_dict(state["accept_val"]) if state["accept_val"] else None
            self.highest_promise = Ballot.from_dict(state["highest_promise"])
            
            print(f"Process {self.process_id} state loaded from disk")
            print(f"Blockchain depth: {self.blockchain.get_depth()}")
            print(f"Balances: {self.bank_account_table.table}")
            return True
            
        except Exception as e:
            print(f"Error loading state for process {self.process_id}: {e}")
            return False

    # Restore state after failure
    async def restore(self):
        print(f"Process {self.process_id} restoring state after failure")
        
        # Load state from disk
        loaded = self.load_state_from_disk()
        print(f"Process {self.process_id} loaded state from disk: {loaded}")
        
        print(f"Process {self.process_id} checking if blockchain matches across all processes")
        
        other_clients = self.get_other_clients()
        max_depth = self.blockchain.get_depth()
        max_depth_node = self.process_id
        
        # Query all other nodes for their depth
        for cid in other_clients:
            try:
                msg = {"id": self.process_id, "type": "QUERY_DEPTH"}
                reply = await self.send_to_client(cid, msg, True)
                
                if reply and reply.get('type') == 'DEPTH_RESPONSE':
                    depth = reply.get('depth')
                    if depth > max_depth:
                        max_depth = depth
                        max_depth_node = cid
            
            except Exception as e:
                print(f"Process {self.process_id} could not query process {cid}: {e}")
                continue
        
        # If this process is behind --> update to get full blockchain
        if max_depth > self.blockchain.get_depth():
            print(f"Process {self.process_id} missing {max_depth - self.blockchain.get_depth()} blocks")
            print(f"Process {self.process_id} requesting blockchain from process {max_depth_node}")
            
            msg = {"id": self.process_id, "type": "REQUEST_BLOCKCHAIN"}
            reply = await self.send_to_client(max_depth_node, msg, True)
            
            if reply and reply.get('type') == 'BLOCKCHAIN_RESPONSE':
                # Reconstruct blockchain and bank accounts
                blockchain_data = reply.get('blockchain')
                self.blockchain.chain = [Block.from_dict(block) for block in blockchain_data]
                
                # Replay all transactions to rebuild bank account table
                self.bank_account_table = BankAccountTable()
                for block in self.blockchain.chain:
                    self.bank_account_table.update(block.sender_id, block.receiver_id, block.amount)
                
                # Reset Paxos state for current depth
                curr_depth = self.blockchain.get_depth()
                self.sequence_no = 0
                self.accept_num = Ballot(-1, -1, curr_depth)
                self.accept_val = None
                self.highest_promise = Ballot(-1, -1, curr_depth)
                
                # Save restored state to disk
                self.save_state_to_disk()
                
                print(f"Blockchain for process {self.process_id} restored to depth {curr_depth}")
                print(f"Process {self.process_id} bank table: {self.bank_account_table.table}")
        
        else:
            print(f"Blockchain for process {self.process_id} is up-to-date")
        
        print(f"Restoration complete for process {self.process_id}")

'''
Start process with given ID & port number.
Command line arguments for process ID and port number
'''

async def main():
    # Retrieve PID from command line arguments
    process_id = int(sys.argv[1]) # should be 0-4
    
    # Load configs (host, ports)
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    HOST = config['host']
    PORTS = config['ports']
    process = Process(process_id=process_id, host=HOST, ports=PORTS)
   
    process.load_state_from_disk()
   
    await asyncio.gather(
        process.start_server(),
        process.handle_user()
    )

asyncio.run(main())