# models/models.py

from pydantic import BaseModel, Field


class CompressRequest(BaseModel):
    container: str = Field(..., example="container_name")
    objects: list[str] = Field(..., example=["thumbnail_0.jpg", "thumbnail_1.jpg"])
    compression_type: str = Field(..., example="zip")
    delete_after_seconds: int = Field(..., example=300)
