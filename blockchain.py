import hashlib
import json
import requests
from textwrap import dedent
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        '''
        Adding a new block to the chain

        :param proof: <int> Proof given by the proof of work algorithm
        :param previous_hash: (Optional) <str> Hash of the previous block

        :return: <dict> New Block

        '''

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        # Resetting list of transactions to be empty
        self.current_transactions = []

        # Adding block to the chain
        self.chain.append(block)

        return block

    def register_node(self, address):
        '''
        Adding a new node to the blockchain

        :param address: <str> Address of node
        :return: None
        '''

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def new_transaction(self, sender, recipient, amount):
        '''
        Creating a new transaction and adding it to the list of transactions

        :param sender: <str> Address of the sender
        :param recipient: <str> Address of the recipient
        :param amount: <int> Amount of transaction

        :return: <int> Index of block
        '''

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        '''
        Creates an SHA-256 hash of a block

        :param block: <dict> Block
        :return: <str>
        '''

        # Ordering the block dictionary by keys then encoding it into JSON
        block_string = json.dumps(block, sort_keys=True).encode()

        # Encoding block_string with sha256 encryption and converting into hex
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        '''
        Defining a simple proof of work algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where
         - p is the previous proof and p' is the new proof

        :param last_proof: <int>
        :return: <int>
        '''

        proof = 0

        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof


    @staticmethod
    def valid_proof(last_proof, proof):
        '''
        Validates the proof by checking if the result of last_proof * proof
        contains four leading zeroes.

        :param last_proof: <int> Previous proof
        :param proof: <int> Current proof
        :return: <boolean> True if correct, False if not
        '''

        # Getting the product of last_proof * proof
        guess = f'{last_proof}{proof}'.encode()

        # Encoding last_proof * proof
        guess_hash = hashlib.sha256(guess).hexdigest()

        # Checking to see if first four characters of hash are zero
        return guess_hash [:4] == "0000"

    def valid_chain(self, chain):
        '''
        Chech a chain to make sure it is valid

        :param chain: <list> Blockchain
        :return: <bool> True if valid, False if not
        '''

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print('\n----------------\n')
            # Check to see if hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check to see if the proofs are correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            # Moving to the next block to check validity
            current_index += 1
            last_block = block

        return True

    def resolve_conflicts(self):
        '''
        Checking to see if any of the other chains are longer,
        therefore newer, than our chain. If any are longer, we
        replace our chain with the longer chain.
        :return: <bool> True if our chain was replaced
        '''

        # Getting all of the other nodes
        neighbors = self.nodes

        # Variable to store a new chain if one is found that is
        # longer than ours
        new_chain = None

        # Setting the length of our chain as the beginning max length
        max_length = len(self.chain)

        # Check all chains to see if they are valid and if they are
        # longer than the current chain
        for node in neighbors:
            # Getting the node's full chain
            response = requests.get(f'http://{node}/chain')

            # Checking to see if the response was valid
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # If the node's chain is both valid and longer than
                # the longest chain, designate as the new chain
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain with the new chain
        if new_chain:
            self.chain = new_chain
            return True

        return False


# Instantiating a node
app = Flask(__name__)

# Creating a globally unique address for the node
node_identifier = str(uuid4()).replace('-', '')

# Instantiating the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # Running the proof of work algorithm to find the proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # Creating a reward for finding the proof.
    # The sender is "0" because a new coin is being created
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1
    )

    # Creating a new block and adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Created",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }

    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Checking to make sure post has required fields
    required = ['sender', 'recipient', 'amount']

    if not all(k in values for k in required):
        return "Missing values", 400

    # Creating a new transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to block {index}'}

    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }

    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    # Getting the values from an incoming request
    values = request.get_json()

    # Getting the nodes from the request
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    # Adding all nodes from request to the chain
    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }

    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }

    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
