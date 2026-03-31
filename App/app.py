from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.schemas import PostCreate, PostResponse, UserRead, UserCreate, UserUpdate
from app.db import Post, create_db_and_tables, get_async_session, User
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import shutil
import os
import uuid
import tempfile
from app.users import auth_backend, current_active_user, fastapi_users


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=app_lifespan)

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix='/auth/jwt', tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])


@app.post("/upload")
async def upload_media(
        uploaded_file: UploadFile = File(...),
        caption_text: str = Form(""),
        current_user: User = Depends(current_active_user),
        db_session: AsyncSession = Depends(get_async_session)
):
    temp_file_location = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.filename)[1]) as temp_file:
            temp_file_location = temp_file.name
            shutil.copyfileobj(uploaded_file.file, temp_file)

        upload_response = imagekit.upload_file(
            file=open(temp_file_location, "rb"),
            file_name=uploaded_file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_name=True,
                tags=["backend-upload"]
            )
        )

        if upload_response.response_metadata.http_status_code == 200:
            new_post = Post(
                user_id=current_user.id,
                caption=caption_text,
                url=upload_response.url,
                file_type="video" if uploaded_file.content_type.startswith("video/") else "image",
                file_name=upload_response.name
            )

            db_session.add(new_post)
            await db_session.commit()
            await db_session.refresh(new_post)

            return new_post

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

    finally:
        if temp_file_location and os.path.exists(temp_file_location):
            os.unlink(temp_file_location)
        uploaded_file.file.close()


@app.get("/feed")
async def fetch_feed(
        db_session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user),
):
    post_query_result = await db_session.execute(select(Post).order_by(Post.created_at.desc()))
    all_posts = [row[0] for row in post_query_result.all()]

    user_query_result = await db_session.execute(select(User))
    all_users = [row[0] for row in user_query_result.all()]
    user_email_map = {user.id: user.email for user in all_users}

    formatted_posts = []
    for single_post in all_posts:
        formatted_posts.append(
            {
                "id": str(single_post.id),
                "user_id": str(single_post.user_id),
                "caption": single_post.caption,
                "url": single_post.url,
                "file_type": single_post.file_type,
                "file_name": single_post.file_name,
                "created_at": single_post.created_at.isoformat(),
                "is_owner": single_post.user_id == current_user.id,
                "email": user_email_map.get(single_post.user_id, "Unknown")
            }
        )

    return {"posts": formatted_posts}


@app.delete("/posts/{post_id}")
async def remove_post(
        post_id: str,
        db_session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user),
):
    try:
        parsed_post_id = uuid.UUID(post_id)

        query_result = await db_session.execute(select(Post).where(Post.id == parsed_post_id))
        target_post = query_result.scalars().first()

        if not target_post:
            raise HTTPException(status_code=404, detail="Post not found")

        if target_post.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to delete this post")

        await db_session.delete(target_post)
        await db_session.commit()

        return {"success": True, "message": "Post deleted successfully"}

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
