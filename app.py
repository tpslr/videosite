from flask import Flask, request, make_response, render_template
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from src import file_upload, auth
from os import environ

load_dotenv()


SITE_NAME = environ.get("SITE_NAME") or __name__

app = Flask(SITE_NAME)
app.config["SQLALCHEMY_DATABASE_URI"] = environ.get("SQLALCHEMY_DATABASE_URI")
app.secret_key = environ.get("FLASK_SECRET_KEY")

IS_DEV = environ.get("ENVIRONMENT") == "dev"

# max content lenght to limit file uploads to 500mb
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024


db = SQLAlchemy(app)

auth.db = db
file_upload.db = db

@app.route("/")
def index():
    return render_template("index.html", title=SITE_NAME)


@app.route("/api/getsession")
def get_session():
    refresh_token = request.headers.get("Authorization")
    session = auth.get_session(refresh_token)
    if type(session) is auth.AuthError:
        return { "error": session }, 401
    
    body = { "user": session.user }
    if session.refresh:
        body["refresh"] = session.refresh
    
    response = make_response(body)
    response.set_cookie("session", session.session_token, secure=not IS_DEV, httponly=True, samesite="Strict")
    return response

@app.route("/api/upload", methods=["POST"])
@auth.requires_auth()
def upload(user: auth.User):
    return file_upload.handle_upload(user.uid)

@app.route("/api/progress/<video_id>")
def progress(video_id):
    return file_upload.get_transcode_progress(video_id)


@app.route("/api/setprogress/<video_id>", methods=["POST"])
# this route is only accessible to localhost, for ffmpeg to report back transcode progress
def set_progress(video_id):
    if request.remote_addr not in ["127.0.0.1", "::1"]:
        return "Forbidden", 403
    return file_upload.set_transcode_progress(video_id)