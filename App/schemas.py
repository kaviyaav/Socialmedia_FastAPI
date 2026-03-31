from pydantic import BaseModel
from fastapi_users import schemas
import uuid


class PostCreate(BaseModel):
    caption: str
    file_url: str


class PostResponse(BaseModel):
    id: uuid.UUID
    caption: str
    file_url: str


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass
