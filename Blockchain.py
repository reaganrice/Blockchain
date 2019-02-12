import hashlib
import json
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request


class Blockchain(object):

	def __init__(self):
		self.chain = []
		self.current_transactions = []

		#Creates the Genesis block
		self.new_block(previous_hash=1, proof=100)

	def new_block(self, proof, previous_hash=None):
		
		'''
		#Creates a new block and adds it to the chain

		:param proof: <int> Proof given by the proof of work algorithm
		:param previous hash: (Optional) <int> Hash of the previous block
		:return: <dict> New Block
		'''
		block = {
			'index': len(self.chain) + 1,
			'timestamp': time(),
			'transactions': self.current_transactions,
			'proof': proof,
			'previous_hash': previous_hash or self.hash(self.chain[-1]),
			}
		
		#Reset the current list of transactions
		self.current_transactions = []

		self.chain.append(block)
		return block

			
	def new_transaction(self, sender, recipient, amount):
		'''
		Adds a new transaction to the transaction list

		:param sender: <str> Address of the Sender
		:param recipient: <str> Address of the Recipient
		:param amount: <int> Amount
		:return: <int> The index of the block that will hold this transaction

		'''
		
		self.current_transactions.append({
			'sender': sender,
			'recipient': recipient,
			'amount': amount,
			})
		return self.last_block['index'] + 1

	
	@staticmethod
	def hash(block):
		
		'''
		Creates a sha-256 hash of a block

		:param block: <dict> Block
		:return: <str>
		'''
		
		# In order to ensure consistency in the hashes, we must order the dictionary
		block_string = json.dumps(block, sort_keys=True).encode()
		return hashlib.sha256(block_string).hexdigest()


	@property
	def last_block(self):

		#Returns the last(most recent) block in the chain

		return self.chain[-1]

	def new_transaction(self, sender, recipient, amount):
		'''
		Creates a new transaction to go into the next mined block

		:param sender: <str> Address of the sender
		:param recipient: <str> Address of the recipient
		:param amount: <amt> Amount
		:return: <int> The index of the block that will hold given amount

		'''

		self.current_transactions.append({
			'sender': sender,
			'recipient': recipient, 
			'amount': amount,
			})
		
		return self.last_block['index'] + 1

			
	@staticmethod
	def valid_proof(last_proof, proof):
		'''
		validates the proof: does hash(last_proof, proof) contain four leading zeroes?

		:param last_proof: <int> Previous proof
		:param proof: <int> Current proof
		:return: <bool> True if correct, False if not
		'''

		guess = f'{last_proof}{proof}'.encode()
		huess_hash = hashlib.sha256(guess).hexdigest()
		return guess_hash[-4] == "0000"
	
	def proof_of_work(last_proof, proof):
	
		'''
		Simple Proof of Work Algorithm:
        - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
        - p is the previous proof, and p' is the new proof
		 :param last_proof: <int>
		 :return: <int>
		'''

		proof = 0
		while self.valid_proof(self, last_proof, proof) is False:
		
			proof =+ 1
		
		return proof


#Instantiation of the node:
app = Flask(__name__)

#Generate a globally(relative) unique address for this node
node_identifier = str(uuid4()).replace('-', '')

#Instantiate the Blockchain
blockchain=Blockchain()	

@app.route('/mine', methods=['GET'])
def mine():
	#Run the proof of work algorithm to get the next proof
	last_block = blockchain.last_block
	last_proof = last_block['proof']
	proof = blockchain.proof_of_work(last_proof)

#A reward must be given after completing the proof
#The sender is "0" to signify that this node has mined the new coin
	blockchain.new_transaction(
		sender="0",
		recipient= node_identifier, 
		amount=1
)

	# Create the new block by adding it to the chain
	previous_hash = blockchain.hash(last_block)
	block = blockchain.new_block(proof, previous_hash)
	
	response = {
		'message': "New block created",
		'index': block["index"],
		'transactions': block["transactions"],
		'proof': block["proof"],
		'previous hash': block["previous hash"],
	}

	return jsonify(response), 200

	
@app.route('/chain', methods=['GET'])
def full_chain():
	response = {
		'chain': blockchain.chain,
		'length': len(blockchain.chain),
		}
	return jsonify.response, 200

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000)

	
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
	values = request.get_json()
	#Check that the required fields are posted in the data
	required = ['sender', 'recipient', 'amount']
	if not all(k in values for k in required):
		return 'Missing Values', 400
		#Create a new Transaction
	index = blocBlockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

	response = {'message': f'Transaction will be added to block {index}'}
	return jsonify(response), 201