from flask import Flask, request, make_response
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from src import auth
from os import environ

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = environ.get("SQLALCHEMY_DATABASE_URI")
app.secret_key = environ.get("FLASK_SECRET_KEY")

IS_DEV = environ.get("ENVIRONMENT") == "dev"

# max content lenght to limit file uploads to 500mb
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024


db = SQLAlchemy(app)

auth.db = db

@app.route("/")
def index():
    return "test"


@app.route("/api/getsession")
def get_session():
    refresh_token = request.headers.get("Authorization")
    session = auth.get_session(refresh_token)
    if session is auth.AuthError:
        return { "error": auth.AuthError }, 401
    
    body = { "user": session.user }
    if session.refresh_token:
        body["refresh_token"] = session.refresh_token
    
    response = make_response(body)
    response.set_cookie("session", session.session_token, secure=not IS_DEV, httponly=True, samesite="Strict")
    return response
