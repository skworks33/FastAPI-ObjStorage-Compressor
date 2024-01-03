# utils/utils.py

import requests
import asyncio
import time
import hmac
import json
import logging
from zipfile import ZipFile
from io import BytesIO
from aiohttp import ClientSession, TraceConfig, TCPConnector
from hashlib import sha1
from config import config
from fastapi import HTTPException


def check_container_exists(token_id: str, project_id: str, container_name: str) -> bool:
    url = f"{config.OS_SWIFT_INT_URL}/v1/AUTH_{project_id}/{container_name}"

    headers = {"X-Auth-Token": token_id}
    response = requests.head(url, headers=headers)

    if response.status_code == 204:
        return True  # コンテナが存在する
    elif response.status_code == 404:
        return False  # コンテナが存在しない
    elif response.status_code == 401:
        error_msg = {"message": "トークンが無効です。", "status": "failure"}
        raise HTTPException(status_code=response.status_code, detail=error_msg)
    else:
        error_msg = {
            "message": f"コンテナの存在確認に失敗しました: ステータスコード={response.status_code}",
            "status": "failure",
        }
        raise HTTPException(status_code=response.status_code, detail=error_msg)


def check_total_size(
    token_id: str, project_id: str, container_name: str, file_names: list[str]
) -> int:
    url_base = f"{config.OS_SWIFT_INT_URL}/v1/AUTH_{project_id}/{container_name}/"
    headers = {"X-Auth-Token": token_id}

    total_size = 0
    missing_files = []

    for file_name in file_names:
        response = requests.head(url_base + file_name, headers=headers)
        if response.status_code == 200:
            file_size = int(response.headers.get("Content-Length", 0))
            total_size += file_size
        elif response.status_code == 404:
            # ファイルが存在しない場合
            missing_files.append(file_name)
        else:
            # その他のエラー
            error_msg = {
                "message": f"ファイル '{file_name}' のサイズ取得中にエラーが発生しました。",
                "status": "failure",
            }
            raise HTTPException(status_code=response.status_code, detail=error_msg)

    if missing_files:
        error_msg = {
            "message": "指定したファイルの一部または全部が存在しません。",
            "status": "failure",
            "missing_files": missing_files,
        }
        raise HTTPException(status_code=404, detail=error_msg)

    return total_size


def setup_trace():
    trace_config = TraceConfig()
    trace_config.on_request_start.append(on_request_start)
    return [trace_config]


async def on_request_start(session, trace_config_ctx, params):
    logging.debug(f"Starting request {params.method} {params.url} {params.headers}")


async def download_and_compress_zip(
    x_auth_token: str,
    project_id: str,
    container_name: str,
    object_names: list[str],
):
    url_base = f"{config.OS_SWIFT_INT_URL}/v1/AUTH_{project_id}/{container_name}/"
    headers = {"X-Auth-Token": x_auth_token}

    zip_buffer = BytesIO()
    connector = TCPConnector(limit=config.CONN_LIMIT)
    with ZipFile(zip_buffer, "w") as zipf:
        async with ClientSession(
            trace_configs=setup_trace(), connector=connector
        ) as session:
            tasks = []
            for object_name in object_names:
                task = download_and_add_to_zip(
                    session, zipf, f"{url_base}{object_name}", headers, object_name
                )
                tasks.append(task)

            try:
                await asyncio.gather(*tasks)  # エラーが発生した場合はここで例外が発生する
            except Exception as e:
                raise e

    zip_buffer.seek(0)
    return zip_buffer.read()


def get_keystone_token(app_cred_id: str, app_cred_secret: str):
    # Keystoneのトークン発行エンドポイント
    url = f"{config.OS_AUTH_URL}/auth/tokens"

    # リクエストボディ
    data = {
        "auth": {
            "identity": {
                "methods": ["application_credential"],
                "application_credential": {
                    "id": app_cred_id,
                    "secret": app_cred_secret,
                },
            }
        }
    }

    # トークン取得リクエスト
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code != 201:
        error_msg = {
            "message": f"トークンの取得に失敗しました: ステータスコード={response.status_code}",
            "status": "failure",
        }
        raise HTTPException(status_code=response.status_code, detail=error_msg)

    # トークンはレスポンスヘッダーのX-Subject-Tokenに含まれる
    return response.headers.get("X-Subject-Token")


# compressed_dataを目的のオブジェクトストレージにアップロード
def swift_upload_file(
    project_id: str, token_id: str, compressed_data: bytes, container: str
) -> str:
    # ファイル名を決定
    file_name = f"{project_id}_{container}_{int(time.time())}.zip"

    path = f"/v1/AUTH_{config.OS_SWIFT_COMP_MGR_PROJECT_ID}/compressed/{file_name}"
    url = f"{config.OS_SWIFT_EXT_URL}{path}"
    headers = {"X-Auth-Token": token_id, "Content-Type": "application/zip"}

    response = requests.put(url, headers=headers, data=compressed_data)

    if response.status_code != 201:
        error_msg = {
            "message": f"ファイルのアップロードに失敗しました: ステータスコード={response.status_code}",
            "status": "failure",
        }
        logging.error(error_msg)
        raise HTTPException(status_code=response.status_code, detail=error_msg)

    return file_name


async def generate_tmp_url(
    object_name: str,
    duration_in_seconds: int = 300,
) -> str:
    expires = int(time.time() + duration_in_seconds)
    path = f"/v1/AUTH_{config.OS_SWIFT_COMP_MGR_PROJECT_ID}/compressed/{object_name}"
    hmac_body = f"GET\n{expires}\n{path}"
    sig = hmac.new(
        config.ACCOUNT_META_TEMP_URL_KEY.encode(),
        hmac_body.encode(),
        sha1,
    ).hexdigest()
    url = (
        f"{config.OS_SWIFT_EXT_URL}{path}?temp_url_sig={sig}&temp_url_expires={expires}"
    )

    return url


async def swift_set_delete_after(
    token_id: str, object_name: str, delete_after_seconds: int
):
    path = f"/v1/AUTH_{config.OS_SWIFT_COMP_MGR_PROJECT_ID}/compressed/{object_name}"
    url = f"{config.OS_SWIFT_INT_URL}{path}"
    headers = {
        "X-Delete-After": str(delete_after_seconds),  # X-Delete-Afterヘッダーを設定
        "X-Auth-Token": token_id,
    }

    connector = TCPConnector(limit=config.CONN_LIMIT)
    async with ClientSession(
        trace_configs=setup_trace(), connector=connector
    ) as session:
        async with session.post(url, headers=headers) as response:
            if response.status != 202:
                error_msg = {
                    "message": f"自動削除設定に失敗しました: ステータスコード={response.status}",
                    "status": "failure",
                }
                raise HTTPException(status_code=response.status, detail=error_msg)


async def download_object(session, url, headers):
    async with session.get(url, headers=headers) as response:
        logging.debug(
            f"Received response: Status {response.status}, Headers {response.headers}"
        )
        if response.status != 200:
            error_msg = {
                "message": f"オブジェクトダウンロードに失敗しました: オブジェクトURL={url}, ステータスコード={response.status}",
                "status": "failure",
            }
            logging.error(error_msg)
            raise HTTPException(status_code=response.status, detail=error_msg)

        return await response.read()


async def download_and_add_to_zip(session, zipf, url, headers, object_name):
    try:
        data = await download_object(session, url, headers)
        if data:
            add_to_zip(zipf, object_name, data)
    except Exception as e:
        raise e


def add_to_zip(zipf, object_name, data):
    try:
        zipf.writestr(object_name, data)
    except Exception as e:
        error_msg = f"ZIPファイルへの書き込みに失敗しました: {e}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)
