import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from PIL import Image

from database import get_db
from models import User, Post, Follow
from config import UPLOAD_DIR, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_SIZE_MB, MAX_POST_CONTENT_LENGTH, PAGE_SIZE
from main import get_current_user

router = APIRouter()


def validate_image(file: UploadFile):
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid image format. Allowed: {ALLOWED_IMAGE_EXTENSIONS}")
    content = file.file.read()
    file.file.seek(0)
    if len(content) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Image too large. Max {MAX_IMAGE_SIZE_MB}MB")


@router.post("/api/posts")
async def create_post(
    content: str = Form(..., max_length=MAX_POST_CONTENT_LENGTH),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    image_path = None
    if image and image.filename:
        validate_image(image)
        filename = f"{uuid.uuid4()}{os.path.splitext(image.filename)[1].lower()}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(image.file.read())
        image_path = f"/uploads/{filename}"

    post = Post(author_id=current_user.id, content=content, image_path=image_path)
    db.add(post)
    db.commit()
    db.refresh(post)

    return {
        "id": post.id,
        "author_id": post.author_id,
        "content": post.content,
        "image_path": post.image_path,
        "created_at": str(post.created_at)
    }


@router.get("/api/posts/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return {
        "id": post.id,
        "author_id": post.author_id,
        "content": post.content,
        "image_path": post.image_path,
        "created_at": str(post.created_at)
    }


@router.delete("/api/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(Post).filter(Post.id == post_id, Post.author_id == current_user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or not authorized")
    if post.image_path:
        filepath = os.path.join(UPLOAD_DIR, os.path.basename(post.image_path))
        if os.path.exists(filepath):
            os.remove(filepath)
    db.delete(post)
    db.commit()
    return {"message": "Post deleted"}


@router.get("/api/users/{user_id}/posts")
def get_user_posts(user_id: int, page: int = Query(1, ge=1), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    posts = db.query(Post).filter(Post.author_id == user_id).order_by(desc(Post.created_at)).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    return [
        {"id": p.id, "author_id": p.author_id, "content": p.content, "image_path": p.image_path, "created_at": str(p.created_at)}
        for p in posts
    ]


@router.get("/api/timeline")
def get_timeline(page: int = Query(1, ge=1), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    followed_ids = [f.followed_id for f in db.query(Follow).filter(Follow.follower_id == current_user.id).all()]
    if not followed_ids:
        return {"posts": [], "page": page, "has_more": False}

    posts = db.query(Post).filter(Post.author_id.in_(followed_ids)).order_by(desc(Post.created_at)).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    total = db.query(Post).filter(Post.author_id.in_(followed_ids)).count()
    has_more = (page * PAGE_SIZE) < total

    return {
        "posts": [
            {"id": p.id, "author_id": p.author_id, "content": p.content, "image_path": p.image_path, "created_at": str(p.created_at)}
            for p in posts
        ],
        "page": page,
        "has_more": has_more
    }
