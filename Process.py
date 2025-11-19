import re
import sys
import json
import yaml
from BankAccountTable import BankAccountTable
from Blockchain import Blockchain
from Block import Block
import asyncio
import yaml

# Class for a single process
class Process:
    # Constructor to initialize process attributes
    def __init__(self, process_id, host, port_number):
        self.process_id = process_id
        self.host = host
        self.port_number = port_number
        self.bank_account_table = BankAccountTable()
        self.blockchain = Blockchain()
        self.alive = True

        self.start_server()

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

    async def parse_data(self, data, writer):
        if data:
            msg = json.loads(data.decode())

            # Check message type
            type = msg.get('type')
            if type == 'PROPOSE':
                pass

            elif type == 'PROMISE':
                pass

            elif type == 'ACCEPT':
                pass

            elif type == 'ACCEPTED':
                pass

            elif type == 'DECIDE':
                pass


    def start_election(self):
        print("Starting election...")
        # Send PREPARE
        # Await PROMISE from majority

    def propose(self):
        print("Starting proposal...")
        # Calculate NONCE
        # Propose block.

    # Runs when majority is accepted
    def accepted(self):
        print("Received accepted from a majority...")
        # If majority accepted: Append block to self.blockchain, update self.bank_account_table.
        # Send DECIDE to all


    # Restore state after failure
    def restore(self):
        print("Restoring process state...")

    # Handles messages from other processes
    def handle_messages(self):
        pass

    # Handle input from the user.
    def handle_user(self):

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
                    self.start_election()

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


# Start process with given ID & port number.
# Command line arguments for process ID and port number
if __name__ == "__main__":
    # Retrieve PID from command line arguments
    process_id = int(sys.argv[1]) # should be 0-4
    
    # Load configs (host, ports)
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    HOST = config['host']
    PORTS = config['ports']
    process = Process(process_id=process_id, host=HOST, port_number=PORTS[process_id])
    process.handle_user()
