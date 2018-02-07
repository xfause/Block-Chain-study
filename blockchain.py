import hashlib
import json
from time import time
from textwrap import dedent
from uuid import uuid4
from flask import Flask
from flask import jsonify,request
from urllib.parse import urlparse
import requests

# block = {
#     'index': 1,
#     'timestamp': 1506057125.900785,
#     'transactions': [
#         {
#             'sender': "8527147fe1f5426f9dd545de4b27ee00",
#             'recipient': "a77f5cdfa2934df3954a5c7c7da5df1f",
#             'amount': 5,
#         }
#     ],
#     'proof': 324984774000,
#     'previous_hash': "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
# }

class Blockchain(object):

    def proof_of_work(self,last_block):

        # 找到一个数字 P 
        # 使得它与前一个区块的 proof 拼接成的字符串的 Hash 值
        # 以 4 个零开头。
        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof,proof,last_hash) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof,proof,last_hash):

        guess_string = str(last_proof) + str(proof) + str(last_hash)
        guess =guess_string.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def __init__(self):

        self.chain = []
        self.current_transcations = []
        self.nodes = set()

        # create first block
        self.new_block(previous_hash=1,proof=100)

    def register_node(self, address):
        # add a new node to the list of nodes
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def new_block(self,previous_hash,proof):
        
        block = {
            'index' : len(self.chain) +1,
            'timestamp': time(),
            'transcations': self.current_transcations,
            'proof': proof,
            'previous_hash':previous_hash or self.hash(self.chain[-1]),
        }

        self.current_transcations = []

        self.chain.append(block)
        return block
    
    def new_transcations(self,sender,recipient,amount):

        self.current_transcations.append({
            'sender' : sender,
            'recipient' : recipient,
            'amount' : amount,
        })
        return self.last_block['index']+1

    @staticmethod
    def hash(block):
        """
        给一个区块生成 SHA-256 值
        :param block: <dict> Block
        :return: <str>
        """
        block_string = json.dumps(block,sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    # check a chain is valid
    def valid_chain(self,chain):

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print('last_block : ' + str(last_block))
            print('block : '+ str(block))
            print('\n------------\n')

            # check hash of block is correct
            if block['previous_hash'] != self.hash(last_block):
                print('Hash Error')
                return False
            
            # check proof of work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], last_block['previous_hash']):
                print('Proof Error')
                return False

            last_block = block
            current_index += 1

        return True

    # resolve diff
    def resolve_conflicts(self):

        #replac chain with the longest one in the network.
        neighbours = self.nodes
        new_chain = None

        max_len = len(self.chain)

        for node in neighbours:
            url = 'http://' + node + '/chain'
            response = requests.get(url)
            
            if response.status_code == 200 :
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_len and self.valid_chain(chain):
                    max_len = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True
        
        return False


# /transactions/new 
# /mine 
# /chain return whole chain
app = Flask(__name__)

node_identifier = str(uuid4()).replace('-','')

blockchain = Blockchain()

@app.route('/mine',methods=['GET'])
def mine():

    # run proof of work algorithm waste time
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # give 1 coin to miner
    # node_identifier is a random uuid in line 95
    blockchain.new_transcations(
        sender = '0',
        recipient = node_identifier,
        amount = 1,
    )

    # add new block in chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof,previous_hash)

    response = {
        'message' : 'New Block Forged',
        'index' : block['index'],
        'transcations' : block['transcations'],
        'proof' : block['proof'],
        'previous_hash' : block['previous_hash'],
    }
    return jsonify(response),200


@app.route('/transcations/new',methods=['POST'])
def new_transcation():
    # {
    #  "sender": "my address",
    #  "recipient": "someone else's address",
    #  "amount": 5
    # }
    values = request.get_json()

    # check required fields are in post data
    required = ['sender','recipient','amount']
    if not all (k in values for k in required):
        return 'Missing values',400

    index = blockchain.new_transcations(values['sender'],values['recipient'],values['amount'])
    response = {'message':'Transaction will add to Block '+str(index)}
    return jsonify(response),201


@app.route('/chain',methods=['GET'])
def full_chain():

    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response),200

@app.route('/nodes/register', methods=['POST'])
def register_node():

    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return 'Error: Please supply a valid list of nodes',400

    for node in nodes:
        blockchain.register_node(node)
    
    response = {
        'message' : 'New nodes have been added',
        'total_nodes' : list(blockchain.nodes),
    }
    return jsonify(response),201

@app.route('/nodes/resolve',methods=['GET'])
def consensus():

    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message' : 'Our chain was replaced',
            'new_chain' : blockchain.chain
        }
    else:
        response = {
            'message' : 'Our chain is authoritative',
            'chain' : blockchain.chain
        }
    return jsonify(response),200

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)