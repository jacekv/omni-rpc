[![CI workflow](https://github.com/jacekv/omni-rpc/actions/workflows/python-ci.yml/badge.svg)](https://github.com/jacekv/omni-rpc/actions/workflows/python-ci.yml)

# Omni RPC

A small service which acts as a proxy for blockchain rpc endpoints.

There is a lot of free rpc endpoints, which allow you to connect to and query
the blockchain. However, these endpoints are often rate limited, can be slow. Or
throw some other errors, forcing you to switch.

This service allows you to connect to multiple rpc endpoints. In the current
state, it sends requests to all rpc providers, merges the results and returns
them to the user.

THe rpc endpoints are taken from [Ethereum-Lists/Chains](https://github.com/ethereum-lists/chains).

Give it a try:

```bash
curl -X POST --data '{"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}' "http://omnirpc.varkiwi.com?chain_id=1"
```

## Running

You can run this service as a docker container, by running the following command:

```bash
docker build -t omni_rpc .
docker run -p 8000:80 omni_rpc
```
And then you can access the service at `http://localhost:8000`.

Here an example of Web3,py code, which connects to the service:

```python
from web3 import Web3

provider = Web3(Web3.HTTPProvider('http://127.0.0.1:8000?chain_id=1'))

block = provider.eth.get_block('latest')
print(block)
```

or using curl:

```bash
curl -X POST --data '{"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":73}' "http://127.0.0.1:8000?chain_id=1"
```

As you can see, you are able to pass the chain_id as a query parameter. This
allows you to connect to different chains.

For supported chains, go to [Ethereum-Lists/Chains](https://github.com/ethereum-lists/chains).

## Development

### Setup

```bash
poetry install
```

### Start virtual environment and server

```bash
poetry shell
uvicorn omni_rpc.main:app --reload
```