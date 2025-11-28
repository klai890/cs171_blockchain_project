import re
import sys
import json
import yaml
from BankAccountTable import BankAccountTable
from Blockchain import Blockchain
from Block import Block
from Ballot import Ballot
import asyncio
from asyncio import as_completed

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
        self.accept_num = None # type Ballot
        self.highest_promise = None # type Ballot
        
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
        print("Received some data", data)
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

            print(f"Received message {msg.get('type')} from process ID {msg.get('id')}")

            # Ignore messages if process is failed
            if not self.alive:
                print("Process is failed, ignoring message")
                # Still send a response so sender doesn't hang
                response = {"id": self.process_id, "type": "FAILED"}
                writer.write(json.dumps(response).encode())
                return

            # Check message type
            type = msg.get('type')

            if type == 'PREPARE':
                print("Processing PREPARE message...")
                proposer_ballot = Ballot.from_dict(msg.get('ballot'))
                print("Ballot received:", proposer_ballot)
                respond = True

                # Acceptor does not accept prepare or accept messages from a contending leader if the depth 
                # of the block being proposed is lower than the acceptor’s depth of its copy of the blockchain
                if proposer_ballot.depth < self.blockchain.get_depth():
                    respond = False

                # If we already sent promise to a proposer w/ higher ballot => ignore
                if self.highest_promise and self.highest_promise > proposer_ballot:
                    respond = False

                # Otherwise, reply with PROMISE
                if respond:
                    self.highest_promise = proposer_ballot
                    send_ballot = self.accept_num if self.accept_num else proposer_ballot
                    msg = {
                        "id": self.process_id, 
                        "type": "PROMISE", 
                        "value": self.accept_val, # can be None or a Block
                        "ballot": send_ballot.to_dict() # proposer's ballot if no prev accepted value
                    }

                    print("Sending message", msg)
                    writer.write(json.dumps(msg).encode())

            elif type == 'ACCEPT':
                print("Processing ACCEPT message...")
                proposer_ballot = Ballot.from_dict(msg.get("ballot"))
                print("Ballot received:", proposer_ballot)
                block = Block.from_dict(msg.get("value"))

                respond = True

                # An acceptor does not accept prepare or accept messages from a contending leader if the depth 
                # of the block being proposed is lower than the acceptor’s depth of its copy of the blockchain
                if proposer_ballot.depth < self.blockchain.get_depth():
                    respond = False

                if self.highest_promise != proposer_ballot:
                    respond = False

                if respond:
                    self.accept_num = proposer_ballot
                    self.accept_val = block
                    msg = {
                        "id": self.process_id,
                        "type": "ACCEPTED",
                        "value": block.to_dict(),
                        "ballot": proposer_ballot
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
                    await self.begin(debit_node, credit_node, amount)

                else:
                    print(f"Node {debit_node} has insufficient funds for transaction.")
                
            # Failed process: Should not send or receive any messages (or respond to user input??)
            elif user_input == "failProcess":
                print("Failing process...")
                self.alive = False

            # Restart process: Resume sending and receiving messages
            elif user_input == "fixProcess":
                print("Fixing process...")
                self.alive = True
                self.restore()

            elif user_input == "printBlockchain":
                print("Printing blockchain...")
                print(self.blockchain)

            elif user_input == "printBalance":
                print("Printing balance...")
                print(self.bank_account_table)

            else:
                print("Invalid user command was entered. Valid commands include:\n- moneyTransfer(debit_node, credit_node, amount), where debit_node and credit_node are 0-4 and amount is a positive number\n- failProcess\n- fixProcess\n- printBlockchain\n- printBalance\n")
    
    '''
    Helper functions
    '''

    # Sends a message to other clients
    async def send_to_client(self, client_id, msg, wait_for_reply=True):
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
        ballot = Ballot(self.sequence_no, self.process_id, self.blockchain.get_depth())
        promises = await self.start_election(ballot)

        print(f"Received {len(promises)} promises: {promises}")

        # Did not receive a majority.
        if len(promises) <= self.num_processes / 2:
            return

        # Process PROMISES to select a block to propose.
        block_to_propose = None

        # See if there is already an accepted block
        non_bottoms = [item for item in promises if item['value'] != 'null']
        
        # Select value with the highest process ID
        if len(non_bottoms) != 0:
            block_to_propose = max(non_bottoms, key=lambda x: x['ballot'])['value']

        # Otherwise, we must create a new Block (mining)
        else:
            previous_hash = None
            block_to_propose = Block(sender, receiver, amount, previous_hash)
            await block_to_propose.calculate_nonce()

        # Propose block
        accepteds = await self.propose(self, ballot, block_to_propose)

        # Did not receive ACCEPTED from majority
        if len(accepteds) <= self.num_processes / 2:
            return
        
        # Otherwise, send decision to all nodes
        await self.decide(block_to_propose, sender, receiver, amount)

    # This process attempts to become leader
    async def start_election(self, ballot):
        print("Starting election...")

        # Send PREPARE to all other clients
        other_clients = self.get_other_clients()
        msg = {"id": self.process_id, "type": "PREPARE", "ballot": ballot.to_dict()} 

        # Await PROMISE from majority
        tasks = [self.send_to_client(cid, msg, True) for cid in other_clients]
        replies = []

        # Proposer implicitly accepts its own ballot
        if self.highest_promise < ballot:
            self.highest_promise = ballot
            replies.append({
                    "id": self.process_id, 
                    "type": "PROMISE", 
                    "value": 'null',
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
            "value": block_to_propose
        } 

        tasks = [self.send_to_client(cid, msg, True) for cid in other_clients]
        replies = []

        # Implicitly accepts its own 
        if self.highest_promise == ballot:
            self.accept_num = ballot
            self.accept_val = block_to_propose
            replies.append({
                "id": self.process_id,
                "type": "ACCEPTED",
                "ballot": ballot.to_dict(),
                "value": block_to_propose,
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
        print("Received accepted from a majority...")
        
        # If majority accepted: Append block to self.blockchain, update self.bank_account_table.
        self.blockchain.add_block(block)
        self.bank_account_table.update(sender, receiver, amount)

        # Send DECIDE to all
        other_clients = self.get_other_clients()
        msg = {
            "id": self.process_id, 
            "type": "DECIDE", 
            "value": block,
            "sender": sender,
            "receiver": receiver,
            "amount": amount
        } 
        
        await asyncio.gather(*(self.send_to_client(cid, msg, False) for cid in other_clients))        

    # Restore state after failure.
    def restore(self):
        print("Restoring process state...")



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
    await asyncio.gather(
        process.start_server(),
        process.handle_user()
    )

asyncio.run(main())