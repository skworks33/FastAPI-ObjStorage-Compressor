from fastapi import FastAPI, Header

import logging
from models.models import CompressRequest
from services.services import compress_objects

# Logging settings
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI()


# ファイルの圧縮を行うエンドポイント
@app.post("/account/v1/{project_id}/object-storage/actions/compress")
async def compress_endpoint(
    project_id: str, compress_request: CompressRequest, x_auth_token: str = Header(None)
):
    return await compress_objects(project_id, compress_request, x_auth_token)
