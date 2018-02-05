import hashlib
import json
from time import time
from uuid import uuid4

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

class blockchain(object):

    def proof_of_work(self,last_proof):

        # 找到一个数字 P 
        # 使得它与前一个区块的 proof 拼接成的字符串的 Hash 值
        # 以 4 个零开头。
        proof = 0
        while self.valid_proof(last_proof,proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof,proof):

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def __init__(self):

        self.chain = []
        self.current_transcations = []

        # create first block
        self.new_block(previous_hash=1,proof=100)

    def new_block(self,previous_hash,proof):
        
        block = {
            'index' : len(self.chain) +1,
            'timestamp': time(),
            'transactions': self.current_transcations,
            'proof': proof,
            'previoous_hash':previous_hash or self.hash(self.chain[-1]),
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

