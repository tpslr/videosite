from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import bcrypt
from flask import request
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
REFRESH_EXPIRY_DAYS = float(environ.get("REFRESH_EXPIRY_DAYS") or 30)
IS_DEV = environ.get("ENVIRONMENT") == "dev"

if not IS_DEV:
    redis = Redis()
    redis.select(1)
    usercache_expire = redis.pubsub()
    usercache_expire.subscribe("usercache_expire")


@dataclass
class User:
    uid: int
    type: UserType
    username: str


@dataclass
class Session:
    user: User
    session_token: str
    refresh: Optional[RefreshToken] = None


@dataclass
class RefreshToken:
    token: str
    expires: int


@dataclass
class AuthError:
    message: str
    display: Optional[bool] = None


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
    if IS_DEV:
        return  # redis isn't used in dev environment
    uid = redis.get(session_token)
    if not uid:
        return
    user = get_user(int(uid))
    if not user:
        return
    sessions[session_token] = Session(user, session_token)


# returns a user session if provided with the correct refresh token, if no
def get_session(refresh_token):
    if not refresh_token:
        user = create_anonymous_user()
        session = create_session(user)
        # only anonymous sessions return refresh token with get_session
        session.refresh = login_anonymous(user)
        return session

    user = user_from_refresh(refresh_token)
    if type(user) is AuthError:
        return user

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
    if not IS_DEV:
        while True:
            # delete all expired entries from usercache
            message = usercache_expire.get_message()
            if not message:
                break
            if message["type"] != "message":
                continue
            if message["data"] not in user_cache:
                continue
            del user_cache[message["data"]]

    if uid in user_cache:
        return user_cache[uid]

    user_data = db.session.execute(text("SELECT type, username FROM users WHERE uid=:uid;"), { "uid": uid }).mappings().fetchone()
    if not user_data:
        return None

    user = User(uid, user_data["type"], user_data["username"])
    user_cache[uid] = user
    return user


# finds a user by refresh token
def user_from_refresh(refresh_token: str):

    result = db.session.execute(text("SELECT uid FROM tokens WHERE token=:token AND expires>now();"), { "token": refresh_token }).fetchone()
    if not result or len(result) < 1:
        # if no result was returned from the db, this means the refresh token didn't exist
        return AuthError("Invalid refresh token.")

    user = get_user(result[0])
    if not user:
        # this should never happen, if the session was valid the user should also be valid
        return AuthError("User not found.")

    return user


# generates a refresh token for an anonymous user
def login_anonymous(user: User):
    if user.type != UserType.anonymous:
        raise ValueError("Tried to anonymous login a non-anonymous user.")

    return generate_refresh(user, ANONYMOUS_EXPIRY_DAYS)


def login_normal(username: str, password: str):
    sql = text("SELECT uid, password FROM users WHERE username=:username;")
    result = db.session.execute(sql, { "username": username }).fetchone()

    if not result:
        return AuthError("Incorrect username", True)

    [uid, pw_hash] = result

    user = get_user(uid)

    if user.type == UserType.anonymous:
        return AuthError("Tried to login as an anonymous user")

    if not bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8")):
        return AuthError("Incorrect password", True)

    return generate_refresh(user, REFRESH_EXPIRY_DAYS)


# generates a refresh token for a user, saves, and returns it
def generate_refresh(user: User, days: float):
    refresh_token = token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=days)

    sql = text("INSERT INTO tokens (uid, token, expires) VALUES (:uid, :token, :expires);")
    db.session.execute(sql, { "uid": user.uid, "token": refresh_token, "expires": expires })
    db.session.commit()
    return RefreshToken(refresh_token, int(expires.timestamp() * 1000))


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


def create_normal_user(username: str, password: str):
    if len(username) < 3:
        return AuthError("Username too short", True)
    if len(password) < 6:
        return AuthError("Password too short", True)

    # make sure the username is free
    if not username_free(username):
        return AuthError("Username taken", True)

    hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    sql = text("INSERT INTO users (type, username, password) VALUES ('normal', :username, :password) RETURNING uid;")
    uid = db.session.execute(sql, { "username": username, "password": hash.decode("utf-8") }).fetchone()[0]
    db.session.commit()

    user = User(uid, UserType.normal, username)
    user_cache[uid] = user

    return generate_refresh(user, REFRESH_EXPIRY_DAYS)


# converts an anonymous user to a normal user
def convert_anonymous_user(username: str, password: str, refresh_token: str):
    if len(username) < 3:
        return AuthError("Username too short", True)
    if len(password) < 6:
        return AuthError("Password too short", True)

    user = user_from_refresh(refresh_token)
    if type(user) is AuthError:
        # AuthError while finding anonymous user
        return user

    if user.type != UserType.anonymous:
        return AuthError("Tried to convert a non-anonymous user")

    if user.username != username:
        # make sure the username is free (only when it's not what it originally was)
        if not username_free(username):
            return AuthError("Username taken", True)

    hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    # save changes to db
    sql = text("UPDATE users SET type='normal', username=:username, password=:password WHERE uid=:uid;")
    db.session.execute(sql, { "uid": user.uid, "username": username, "password": hash.decode("utf-8") })
    db.session.commit()

    # save changes to cache
    user.type = UserType.normal
    user.username = username

    if not IS_DEV:
        # tell all the other workers this users cached data has expired
        redis.publish("usercache-expire", user.uid)

    return generate_refresh(user, REFRESH_EXPIRY_DAYS)
