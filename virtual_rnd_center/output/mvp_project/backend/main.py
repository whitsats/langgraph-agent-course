import os
import re
import random
import string
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, EmailStr
import bcrypt
from PIL import Image

from database import engine, get_db, Base
from models import User, Post, Follow, VerificationCode
from config import (
    UPLOAD_DIR, SECRET_KEY, VERIFICATION_CODE_EXPIRE_MINUTES,
    MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES, ALLOWED_IMAGE_EXTENSIONS,
    MAX_IMAGE_SIZE_MB, MAX_POST_CONTENT_LENGTH, PAGE_SIZE
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LightQuotes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory session store (session_token -> user_id)
sessions = {}
# Login attempt tracking (ip -> {"attempts": int, "locked_until": datetime})
login_attempts = {}


def generate_session_token():
    return "".join(random.choices(string.ascii_letters + string.digits, k=64))


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("session_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    user_id = sessions.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def generate_verification_code():
    return "".join(random.choices(string.digits, k=6))


@app.get("/health")
def health():
    return {"status": "ok"}


# ----- Auth Routes -----

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    code: str


@app.post("/api/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == req.username) | (User.email == req.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already taken")

    vc = db.query(VerificationCode).filter(
        VerificationCode.email == req.email,
        VerificationCode.code == req.code,
        VerificationCode.used == 0,
        VerificationCode.expires_at > datetime.utcnow()
    ).first()
    if not vc:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    vc.used = 1
    password_hash = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(username=req.username, email=req.email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = generate_session_token()
    sessions[token] = user.id

    resp = JSONResponse({"id": user.id, "username": user.username, "email": user.email})
    resp.set_cookie(key="session_token", value=token, httponly=True, max_age=86400 * 7)
    return resp


class SendCodeRequest(BaseModel):
    email: EmailStr


@app.post("/api/auth/send-code")
def send_code(req: SendCodeRequest, db: Session = Depends(get_db)):
    code = generate_verification_code()
    expires_at = datetime.utcnow() + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)
    vc = VerificationCode(email=req.email, code=code, expires_at=expires_at)
    db.add(vc)
    db.commit()
    # In MVP, log code to console instead of sending real email
    print(f"[VERIFICATION CODE] Email: {req.email}, Code: {code}")
    return {"message": "Verification code sent (check console)", "code_debug": code}


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host
    now = datetime.utcnow()

    if ip in login_attempts:
        if login_attempts[ip]["locked_until"] and login_attempts[ip]["locked_until"] > now:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    user = db.query(User).filter(User.email == req.email).first()
    if not user or not bcrypt.checkpw(req.password.encode("utf-8"), user.password_hash.encode("utf-8")):
        if ip not in login_attempts:
            login_attempts[ip] = {"attempts": 0, "locked_until": None}
        login_attempts[ip]["attempts"] += 1
        if login_attempts[ip]["attempts"] >= MAX_LOGIN_ATTEMPTS:
            login_attempts[ip]["locked_until"] = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if ip in login_attempts:
        login_attempts[ip] = {"attempts": 0, "locked_until": None}

    token = generate_session_token()
    sessions[token] = user.id

    resp = JSONResponse({"id": user.id, "username": user.username, "email": user.email})
    resp.set_cookie(key="session_token", value=token, httponly=True, max_age=86400 * 7)
    return resp


@app.post("/api/auth/logout")
def logout(request: Request):
    token = request.cookies.get("session_token", "")
    sessions.pop(token, None)
    resp = JSONResponse({"message": "Logged out"})
    resp.delete_cookie("session_token")
    return resp


@app.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email, "bio": current_user.bio}


# ----- User Routes -----

@app.get("/api/users/discover")
def discover_users(page: int = Query(1, ge=1), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    followed_ids = [f.followed_id for f in db.query(Follow).filter(Follow.follower_id == current_user.id).all()]
    excluded = followed_ids + [current_user.id]
    users = db.query(User).filter(~User.id.in_(excluded)).order_by(desc(User.created_at)).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    return [{"id": u.id, "username": u.username, "bio": u.bio, "created_at": str(u.created_at)} for u in users]


@app.get("/api/users/{user_id}")
def get_user_profile(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    is_following = db.query(Follow).filter(Follow.follower_id == current_user.id, Follow.followed_id == user_id).first() is not None
    return {"id": user.id, "username": user.username, "bio": user.bio, "created_at": str(user.created_at), "is_following": is_following}


@app.post("/api/users/{user_id}/follow")
def follow_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(Follow).filter(Follow.follower_id == current_user.id, Follow.followed_id == user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already following this user")
    follow = Follow(follower_id=current_user.id, followed_id=user_id)
    db.add(follow)
    db.commit()
    return {"message": "Now following"}


@app.delete("/api/users/{user_id}/follow")
def unfollow_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Follow).filter(Follow.follower_id == current_user.id, Follow.followed_id == user_id).first()
    if not existing:
        raise HTTPException(status_code=400, detail="Not following this user")
    db.delete(existing)
    db.commit()
    return {"message": "Unfollowed"}
