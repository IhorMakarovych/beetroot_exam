from models import User, engine
from sqlmodel import Session, select
from passlib.hash import bcrypt
from fastapi import Response, Cookie, HTTPException
import secrets

SESSION_COOKIE = 'session_token'

def register_user(username: str, password: str):
    with Session(engine) as s:
        q = s.exec(select(User).where(User.username == username)).first()
        if q:
            return None
        user = User(username=username, password_hash=bcrypt.hash(password))
        s.add(user)
        s.commit()
        s.refresh(user)
        return user

def require_user(username: str, password: str):
    with Session(engine) as s:
        user = s.exec(select(User).where(User.username == username)).first()
        if not user: return None
        if not user.verify_password(password): return None
        return user

def login_user(response: Response, user: User):
    token = secrets.token_hex(16)
    user.session_token = token
    with Session(engine) as s:
        s.add(user)
        s.commit()
    response.set_cookie(SESSION_COOKIE, token, httponly=True, max_age=7*24*3600)

def logout_user(response: Response):
    response.delete_cookie(SESSION_COOKIE)

def get_current_user(session_token: str | None = Cookie(None)):
    if not session_token:
        raise HTTPException(status_code=401, detail='Not authenticated')
    with Session(engine) as s:
        user = s.exec(select(User).where(User.session_token == session_token)).first()
        if not user:
            raise HTTPException(status_code=401, detail='Invalid session')
        return user
