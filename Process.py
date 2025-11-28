import re
import sys
import json
import yaml
from BankAccountTable import BankAccountTable
from Blockchain import Blockchain
from Block import Block
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
        self.accept_num = None # Format (seq_num, pid, depth)
        self.highest_promise = None # Format (seq_num, pid, depth)
        
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

            # Check message type
            type = msg.get('type')

            if type == 'PREPARE':
                (proposer_seq_num, proposer_id, proposer_depth) = msg.get('ballot')
                respond = True

                # Acceptor does not accept prepare or accept messages from a contending leader if the depth 
                # of the block being proposed is lower than the acceptor’s depth of its copy of the blockchain
                if proposer_depth < self.blockchain.depth():
                    respond = False

                # If we already sent promise to a proposer w/ higher ballot => ignore
                if self.highest_promise:
                    (promised_seq_num, promised_id, promised_depth) = self.highest_promise
                    if promised_seq_num > proposer_seq_num: 
                        respond = False

                    elif promised_seq_num == proposer_seq_num and promised_id > proposer_id:
                        respond = False


                # Otherwise, reply with PROMISE
                if respond:
                    self.highest_promise = msg.get("ballot")
                    send_ballot = self.accept_num if self.accept_num else msg.get("ballot")
                    msg = {
                        "id": self.process_id, 
                        "type": "PROMISE", 
                        "value": self.accept_val, # can be None
                        "ballot": send_ballot # proposer's ballot if no prev accepted value
                    }

                    writer.write(json.dumps(msg).encode())

            elif type == 'PROPOSE':
                pass

            elif type == 'ACCEPT':
                pass

            elif type == 'DECIDE':
                pass

    '''
    Handle user input
    '''
    # Handle input from the user.
    async def handle_user(self):

        while True:
            user_input = input().strip()

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
                    await self.begin()

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
        
        except TimeoutError:
            print(f"Timeout while waiting for Client {client_id}'s response.")
            return None

        except ConnectionRefusedError:
            print(f"Connection to Client {client_id} refused.")
            return None

    '''
    PAXOS functions
    '''

    # First, PREPARE. If successful, PROPOSE. If successful, ACCEPT. If successful, DECIDE.
    async def begin(self):
        promises = await self.start_election()

        # Process PROMISES to select a value to propose.


    # This process attempts to become leader
    async def start_election(self):
        print("Starting election...")

        # Send PREPARE to all other clients
        other_clients = [i for i in range(5) if i != self.process_id]
        ballot = (self.sequence_no, self.process_id, self.blockchain.get_depth())  # Ballot = (seq_num, pid, depth)
        msg = {"id": self.process_id, "type": "PREPARE", "ballot": ballot} 

        # Await PROMISE from majority
        tasks = [self.send_to_client(cid, msg, True) for cid in other_clients]
        replies = []

        for completed_task in as_completed(tasks):
            reply = await completed_task
            replies.append(reply)

            # Majority?
            if len(replies) > self.num_processes / 2:
                break

        # Received PROMISE from majority.
        return replies


    # This process believes it is leader & proposes a value.
    def propose(self):
        print("Starting proposal...")
        # Calculate NONCE
        # Propose block.

    # This process has received majority accepted values, must decide
    def decide(self):
        print("Received accepted from a majority...")
        # If majority accepted: Append block to self.blockchain, update self.bank_account_table.
        # Send DECIDE to all

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