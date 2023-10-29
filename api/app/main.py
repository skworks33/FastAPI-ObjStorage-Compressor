from fastapi import FastAPI, Field
from pydantic import BaseModel

app = FastAPI()

class CompressRequest(BaseModel):
    container: str = Field(..., example="container_name")
    objects: list[str] = Field(..., example=["object_name1", "object_name2"])
    compression_type: str = Field(..., example="zip")
    delete_after_seconds: int = Field(..., example=300)

@app.post("/account/v1/{project_id}/object-storage/actions/compress")
async def compress_objects(project_id: str, compress_request: CompressRequest):
    # TODO: ファイルの存在チェック
    if not check_file_exists(compress_request.container, compress_request.objects):
        return {"error": "File does not exist"}

    # TODO: ファイルの合計サイズが5GBを超えないかチェック。超える場合は拒否する予定。
    if is_over_5GB(compress_request.container, compress_request.objects):
        return {"error": "File size exceeds 5GB"}

    # TODO: ストリーミング方式でオブジェクトストレージからファイルをダウンロード
    file_stream = stream_file(compress_request.container, compress_request.objects)

    # TODO: 逐次的にデータを圧縮
    compressed_data = compress_on_the_fly(file_stream, compress_request.compression_type)

    # TODO: 圧縮したデータをオブジェクトストレージにアップロード
    # (5GBを超える場合は分割アップロードするかも, 一定サイズに達したら、その部分をアップロードするかも)
    upload_file(compressed_data, compress_request.container)

    # TODO: 圧縮したファイルに対して X-Delete-After ヘッダで自動削除を設定
    set_delete_after(compress_request.delete_after_seconds)

    # TODO: tmp_url を生成
    tmp_url = generate_tmp_url()

    # TODO: 不要になったファイルを削除
    delete_unnecessary_files()

    # TODO: tmp_url を返却
    return {"tmp_url": tmp_url}

# 各TODOに相当する関数のスケルトン（実装は仮）
def check_file_exists(container, objects):
    pass

def is_over_5GB(container, objects):
    pass

def stream_file(container, objects):
    pass

def compress_on_the_fly(file_stream, compression_type):
    pass

def upload_file(compressed_data, container):
    pass

def set_delete_after(delete_after_seconds):
    pass

def generate_tmp_url():
    pass

def delete_unnecessary_files():
    pass
