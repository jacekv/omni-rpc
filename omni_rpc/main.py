from fastapi import FastAPI

from omni_rpc.custom_logging import logger
from omni_rpc.routers import proxy_rpc

app = FastAPI()


logger.info("Starting Omni RPC server")
app.include_router(proxy_rpc.router)
