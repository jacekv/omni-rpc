from fastapi import FastAPI
from fastapi import Request

from omni_rpc.routers import proxy_rpc

app = FastAPI()

app.include_router(proxy_rpc.router)
# async def main_route(chain_id: int):
# @app.post("/")
# async def proxy_rpc_message(chain_id: int, request: Request):
#     print('ChainID', chain_id)
#     #Steps:
#     # Check if the chain_id is valid by checking the files
#     # If valid, then get the providers
#     # If not valid, return error
#     # Forward request to providers
#     # MErge response and return
#     body = await request.json()
#     print(body)
#     return {"message": "Hey, It is me Goku"}
