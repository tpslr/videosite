from dotenv import load_dotenv
from os import environ
from flask import Flask


load_dotenv()


SITE_NAME = environ.get("SITE_NAME") or "videosite"
BASE_URL = environ.get("BASE_URL") or "http://localhost:5000"
VIDEO_FOLDER = environ.get("VIDEO_FOLDER") or "video_data"

ANONYMOUS_EXPIRY_DAYS = float(environ.get("ANONYMOUS_EXPIRY_DAYS") or 30)
REFRESH_EXPIRY_DAYS = float(environ.get("REFRESH_EXPIRY_DAYS") or 30)

IS_DEV = environ.get("ENVIRONMENT") == "dev"


def set_config(app: Flask):
    app.config["SQLALCHEMY_DATABASE_URI"] = environ.get("SQLALCHEMY_DATABASE_URI")
    app.secret_key = environ.get("FLASK_SECRET_KEY")

    # pool_pre_ping to prevent server from erroring due to database connections expiring
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}

    # session cookie cannot be named "session", since a cookie with that name is used for other things
    app.config["SESSION_COOKIE_NAME"] = "vvc"

    # max content lenght to limit file uploads to 500mb
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
