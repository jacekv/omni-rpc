from fastapi import APIRouter
from fastapi import Request
from fastapi import Response
from starlette.status import HTTP_404_NOT_FOUND

from omni_rpc.custom_logging import logger
from omni_rpc.providers.providers import check_provider_availability
from omni_rpc.providers.providers import forward_request
from omni_rpc.providers.providers import get_chain_providers

router = APIRouter()


@router.post("/")
async def proxy_rpc(chain_id: int, request: Request, response: Response):
    logger.info(f"Received request for chain_id: {chain_id}")
    if not check_provider_availability(chain_id):
        response.status_code = HTTP_404_NOT_FOUND
        logger.info(f"Chain id {chain_id} not found.")
        return {"detail": "Chain id not found."}

    providers = get_chain_providers(chain_id)

    body = await request.json()
    response_body = forward_request(body, providers)

    return response_body
