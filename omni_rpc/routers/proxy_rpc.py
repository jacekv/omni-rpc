from fastapi import APIRouter
from fastapi import Request

from omni_rpc.providers.providers import check_provider_availability

router = APIRouter()


@router.post("/", tags=["users"])
async def read_users(chain_id: int, request: Request):
    print("ChainID", chain_id)
    print(check_provider_availability(chain_id))
    # Steps:
    # Check if the chain_id is valid by checking the files
    # If valid, then get the providers
    # If not valid, return error
    # Forward request to providers
    # MErge response and return
    body = await request.json()
    print(body)
    print(__file__)
    return {"message": "Hey, It is me Goku"}
