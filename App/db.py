from collections.abc import AsyncGenerator
import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
from fastapi_users.db import SQLAlchemyUserDatabase, SQLAlchemyBaseUserTableUUID
from fastapi import Depends

DATABASE_URL = "sqlite+aiosqlite:///./test.db"


class BaseModel(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, BaseModel):
    posts = relationship("Post", back_populates="owner")


class Post(BaseModel):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    caption = Column(Text)
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="posts")


engine = create_async_engine(DATABASE_URL)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def initialize_database():
    async with engine.begin() as connection:
        await connection.run_sync(BaseModel.metadata.create_all)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_db_session)):
    yield SQLAlchemyUserDatabase(session, User)
