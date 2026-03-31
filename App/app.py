from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.schemas import PostCreate, PostResponse, UserRead, UserCreate, UserUpdate
from app.db import Post, initialize_database, get_db_session, User
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit_client as imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import shutil
import os
import uuid
import tempfile
from app.users import auth_backend, current_active_user, fastapi_users


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    await initialize_database()
    yield


app = FastAPI(lifespan=app_lifespan)

# 🔐 Auth routes
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix='/auth/jwt', tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])


# 📤 Upload API
@app.post("/upload")
async def upload_media(
    uploaded_file: UploadFile = File(...),
    caption_text: str = Form(""),
    current_user: User = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_db_session)
):
    temp_file_location = None

    try:
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.filename)[1]) as temp_file:
            temp_file_location = temp_file.name
            shutil.copyfileobj(uploaded_file.file, temp_file)

        # Upload to ImageKit
        upload_response = imagekit.upload_file(
            file=open(temp_file_location, "rb"),
            file_name=uploaded_file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_name=True,
                tags=["backend-upload"]
            )
        )

        # Save post in DB
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


# 📰 Feed API
@app.get("/feed")
async def fetch_feed(
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(current_active_user),
):
    # Fetch posts
    post_query = await db_session.execute(
        select(Post).order_by(Post.created_at.desc())
    )
    all_posts = post_query.scalars().all()

    # Fetch users
    user_query = await db_session.execute(select(User))
    all_users = user_query.scalars().all()
    user_email_map = {user.id: user.email for user in all_users}

    # Format response
    formatted_posts = []
    for post in all_posts:
        formatted_posts.append(
            {
                "id": str(post.id),
                "user_id": str(post.user_id),
                "caption": post.caption,
                "url": post.url,
                "file_type": post.file_type,
                "file_name": post.file_name,
                "created_at": post.created_at.isoformat(),
                "is_owner": post.user_id == current_user.id,
                "email": user_email_map.get(post.user_id, "Unknown")
            }
        )

    return {"posts": formatted_posts}


# ❌ Delete Post API
@app.delete("/posts/{post_id}")
async def remove_post(
    post_id: str,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(current_active_user),
):
    try:
        parsed_post_id = uuid.UUID(post_id)

        query_result = await db_session.execute(
            select(Post).where(Post.id == parsed_post_id)
        )
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
