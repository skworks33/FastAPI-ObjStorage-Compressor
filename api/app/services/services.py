# services/services.py

from models.models import CompressRequest
from fastapi import HTTPException
from config import config
import requests
import json
from utils.utils import (
    download_and_compress_zip,
    get_keystone_token,
    swift_upload_file,
    swift_set_delete_after,
    generate_tmp_url,
    check_container_exists,
    check_total_size,
)


async def compress_objects(
    project_id: str, compress_request: CompressRequest, x_auth_token: str
) -> dict:
    # コンテナの存在チェック
    try:
        if not check_container_exists(
            x_auth_token, project_id, compress_request.container
        ):
            error_response = {
                "message": f"コンテナ '{compress_request.container}' が存在しません。",
                "status": "failure",
            }
            raise HTTPException(status_code=400, detail=error_response)
    except HTTPException as e:
        raise e

    # ファイルサイズの合計が5GBを超えている場合はエラー
    try:
        total_size = check_total_size(
            x_auth_token,
            project_id,
            compress_request.container,
            compress_request.objects,
        )
        max_file_size = 5 * 1024 * 1024 * 1024  # 5GB
        print("total_size:" + str(total_size))  # debug
        if total_size > max_file_size:
            error_response = {"message": "ファイルサイズの合計が5GBを超えています。", "status": "failure"}
            raise HTTPException(status_code=400, detail=error_response)
    except HTTPException as e:
        raise e

    # メインの処理
    try:
        # ファイルのダウンロードと逐次的なZIPへの圧縮
        zip_bytes = await download_and_compress_zip(
            x_auth_token,
            project_id,
            compress_request.container,
            compress_request.objects,
        )

        # OpenStack SwiftのAPIを使ってオブジェクトストレージにアップロードする処理のため、トークンを取得する
        mgr_x_auth_token = get_keystone_token(
            config.OS_SWIFT_COMP_MGR_USER_CREDENTIAL_ID,
            config.OS_SWIFT_COMP_MGR_USER_CREDENTIAL_SECRET,
        )

        # 全ての圧縮が終わったらオブジェクトストレージにアップロード
        compressed_file_name = swift_upload_file(
            project_id, mgr_x_auth_token, zip_bytes, compress_request.container
        )

        # 圧縮したファイルに対して X-Delete-After ヘッダで自動削除を設定
        await swift_set_delete_after(
            mgr_x_auth_token,
            compressed_file_name,
            compress_request.delete_after_seconds,
        )

        # tmp_url を生成
        tmp_url = await generate_tmp_url(
            compressed_file_name, compress_request.delete_after_seconds
        )

    except HTTPException as e:
        # 既存のHTTPExceptionのハンドリング
        raise e

    except RuntimeError as runtime_exc:
        # 既存のRuntimeErrorのハンドリング
        error_response = {
            "message": f"{runtime_exc}",
            "status": "failure",
        }
        raise HTTPException(status_code=500, detail=error_response)

    except requests.RequestException as req_exc:
        # ネットワークリクエスト関連のエラー
        error_response = {
            "message": f"ネットワークエラーが発生しました: {req_exc}",
            "status": "failure",
        }
        raise HTTPException(status_code=500, detail=error_response)

    except Exception as exc:
        # その他の予期しないエラー
        error_response = {"message": f"予期しないエラーが発生しました: {exc}", "status": "failure"}
        raise HTTPException(status_code=500, detail=error_response)

    # 正常なレスポンスを返却
    return {
        "compress": {
            "compressed_file_url": tmp_url,
            "delete_after_seconds": compress_request.delete_after_seconds,
            "status": "success",
        }
    }
