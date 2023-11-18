from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from flask import request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from secrets import token_urlsafe
from enum import Enum
from random_username.generate import generate_username
from datetime import datetime, timedelta
from os import environ
from functools import wraps

db: SQLAlchemy = None

sessions: dict[str, Session] = {}

user_cache: dict[int, User] = {}

ANONYMOUS_EXPIRY_DAYS = float(environ.get("ANONYMOUS_EXPIRY_DAYS"))    

@dataclass
class User:
    uid: int
    type: UserType
    username: str

@dataclass
class Session:
    user: User
    session_token: str
    refresh_token: Optional[str] = None

@dataclass
class AuthError:
    message: str

class UserType(str, Enum):
    anonymous = "anonymous"
    normal = "normal"
    admin = "admin"

# decorator to wrap a request function with, makes sure user session is valid and passes user object as first argument
def requires_auth():
    def _requires_auth(f):
        @wraps(f)
        def __requires_auth(*args, **kwargs):
            if "session" not in request.cookies:
                return "Unauthorized", 401
            
            session_token = request.cookies.get("session")

            # checks the session token for validity
            if session_token not in sessions:
                return "Unauthorized", 401
            
            user = sessions[session_token].user
            # call the function this decorator is on
            return f(user, *args, **kwargs)
        return __requires_auth
    return _requires_auth

# returns a user session if provided with the correct refresh token, if no 
def get_session(refresh_token):
    if not refresh_token:
        user = create_anonymous_user()
        session = create_session(user)
        # only anonymous sessions return refresh token with get_session
        session.refresh_token = login_anonymous(user)
        return session
    
    uid = db.session.execute(text("SELECT uid FROM tokens WHERE token=:token;"), { "token": refresh_token }).fetchone()[0]
    if not uid:
        # if no uid was returned from the db, this means the refresh token didn't exist
        return AuthError("Invalid refresh token.")
    
    user = get_user(uid)
    if not user:
        # this should never happen, if the session was valid the user should also be valid
        return AuthError("User not found.")
    
    session = create_session(user)

    return session

# makes sure a username is not being used
def username_free(username: str):
    return not db.session.execute(text("SELECT uid FROM users WHERE username=:username;"), { "username": username }).mappings().fetchone()

# generates a session token for a user
def create_session(user: User):
    token = token_urlsafe(32)
    session = Session(user, token)
    sessions[token] = session
    return session

# loads a user from cache or db by user id
def get_user(uid: int):
    if uid in user_cache:
        return user_cache[uid]
    
    user_data = db.session.execute(text("SELECT type, username FROM users WHERE uid=:uid;"), { "uid": uid }).mappings().fetchone()
    if not user_data:
        return None
    
    user = User(uid, user_data["type"], user_data["username"])
    user_cache[uid] = user
    return user

# generates a refresh token for an anonymous user
def login_anonymous(user: User):
    if user.type != UserType.anonymous:
        raise ValueError("Tried to anonymous login a non-anonymous user.")
    refresh_token = token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(days=ANONYMOUS_EXPIRY_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
    db.session.execute(text("INSERT INTO tokens (uid, token, expires) VALUES (:uid, :token, :expires);"), { "uid": user.uid, "token": refresh_token, "expires": expires })
    db.session.commit()
    return refresh_token

def create_anonymous_user():
    username = ""
    # generate a random username and check that it's free
    while not username or not username_free(username):
        username = generate_username()[0]
    
    uid = db.session.execute(text("INSERT INTO users (type, username) VALUES ('anonymous', :username) RETURNING uid;"), { "username": username }).fetchone()[0]
    db.session.commit()

    user = User(uid, UserType.anonymous, username)
    user_cache[uid] = user
    return user