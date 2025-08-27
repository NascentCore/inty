from fastapi import File, UploadFile
from pydantic import BaseModel


class ImageUploadRequest(BaseModel):
    file: UploadFile = File(...)
    enable_cropping: bool = False
