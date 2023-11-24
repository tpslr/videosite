from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from flask import request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from secrets import token_urlsafe
from enum import Enum
from random_username.generate import generate_username
from datetime import datetime, timedelta, timezone
from os import environ
from functools import wraps
from redis import Redis

db: SQLAlchemy = None


sessions: dict[str, Session] = {}

user_cache: dict[int, User] = {}

ANONYMOUS_EXPIRY_DAYS = float(environ.get("ANONYMOUS_EXPIRY_DAYS"))    
IS_DEV = environ.get("ENVIRONMENT") == "dev"

if not IS_DEV:
    redis = Redis()
    redis.select(1)

@dataclass
class User:
    uid: int
    type: UserType
    username: str

@dataclass
class Session:
    user: User
    session_token: str
    refresh: Optional[AnonymousRefresh] = None

@dataclass
class AnonymousRefresh:
    token: str
    expires: int

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

            if session_token not in sessions:
                # if session token isn't cached, try to load session from redis
                session_from_redis(session_token)

            # checks the session token for validity
            if session_token not in sessions:
                return "Unauthorized", 401
            
            user = sessions[session_token].user
            # call the function this decorator is on
            return f(user, *args, **kwargs)
        return __requires_auth
    return _requires_auth

# loads session data from redis
def session_from_redis(session_token):
    if IS_DEV: return # redis isn't used in dev environment
    uid = redis.get(session_token)
    if not uid: return
    user = get_user(int(uid))
    if not user: return
    sessions[session_token] = Session(user, session_token)

# returns a user session if provided with the correct refresh token, if no 
def get_session(refresh_token):
    if not refresh_token:
        user = create_anonymous_user()
        session = create_session(user)
        # only anonymous sessions return refresh token with get_session
        session.refresh = login_anonymous(user)
        return session
    
    result = db.session.execute(text("SELECT uid FROM tokens WHERE token=:token AND expires<now();"), { "token": refresh_token }).fetchone()
    if not result or len(result) < 1:
        # if no result was returned from the db, this means the refresh token didn't exist
        return AuthError("Invalid refresh token.")
    
    user = get_user(result[0])
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
    if not IS_DEV:
        redis.mset({ token: user.uid })
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
    expires = datetime.now(timezone.utc) + timedelta(days=ANONYMOUS_EXPIRY_DAYS)

    sql = text("INSERT INTO tokens (uid, token, expires) VALUES (:uid, :token, :expires);")
    db.session.execute(sql, { "uid": user.uid, "token": refresh_token, "expires": expires })
    db.session.commit()
    return AnonymousRefresh(refresh_token, int(expires.timestamp() * 1000))

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