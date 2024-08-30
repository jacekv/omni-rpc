from fastapi import FastAPI
from fastapi import Request

import omni_rpc.custom_logging as custom_logging
from omni_rpc.routers import proxy_rpc

app = FastAPI()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    custom_logging.trace_id = custom_logging.get_trace_id()
    response = await call_next(request)
    return response


app.include_router(proxy_rpc.router)
