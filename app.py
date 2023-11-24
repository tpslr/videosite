from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, make_response, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from src import file_upload, auth, view_count, helpers
from os import environ



SITE_NAME = environ.get("SITE_NAME") or __name__
BASE_URL = environ.get("BASE_URL") or "http://localhost:5000"
VIDEO_FOLDER = environ.get("VIDEO_FOLDER")

app = Flask(SITE_NAME)
app.config["SQLALCHEMY_DATABASE_URI"] = environ.get("SQLALCHEMY_DATABASE_URI")
app.config["SESSION_COOKIE_NAME"] = "vvc"
app.secret_key = environ.get("FLASK_SECRET_KEY")

IS_DEV = environ.get("ENVIRONMENT") == "dev"

# max content lenght to limit file uploads to 500mb
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024


db = SQLAlchemy(app)

auth.db = db
file_upload.db = db
view_count.db = db

@app.route("/")
def index():
    return render_template("index.html", header_title=SITE_NAME, title=SITE_NAME)


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

@app.route("/api/login", methods=["POST"])
@helpers.requires_form_data({ "username": str, "password": str })
def login():
    refresh = auth.login_normal(request.form["username"], request.form["password"])
    
    if type(refresh) is auth.AuthError:
        return { "error": refresh }
    
    return { "refresh": refresh }

@app.route("/api/signup", methods=["POST"])
@helpers.requires_form_data({ "username": str, "password": str })
def signup():
    refresh = auth.create_normal_user(request.form["username"], request.form["password"])

    if type(refresh) is auth.AuthError:
        return { "error": refresh }
    
    return { "refresh": refresh }

@app.route("/api/upload", methods=["POST"])
@auth.requires_auth()
def upload(user: auth.User):
    return file_upload.handle_upload(user.uid)

@app.route("/api/progress/<video_id>")
def progress(video_id):
    return file_upload.get_transcode_progress(video_id)

@app.route("/api/videos")
@auth.requires_auth()
def videos(user: auth.User):
    limit = request.args["limit"] if "limit" in request.args else "20"
    offset = request.args["offset"] if "offset" in request.args else "0"
    try:
        limit = int(limit)
    except:
        return { "error": { "message": "missing arg limit" } }, 400
    try:
        offset = int(offset)
    except:
        return { "error": { "message": "missing arg offset" } }, 400
    
    if "public" in request.args:
        sql = text("SELECT id, views, duration, title, owner FROM videos WHERE owner!=:owner ORDER BY upload_date DESC LIMIT(:limit) OFFSET(:offset*:limit);")
    else:
        sql = text("SELECT id, views, duration, title FROM videos WHERE owner=:owner AND private=false ORDER BY upload_date DESC LIMIT(:limit) OFFSET(:offset*:limit);")
    videos = db.session.execute(sql, { "owner": user.uid, "limit": limit, "offset": offset }).mappings().fetchall()
    videos = [dict(video) for video in videos]

    if "public" in request.args:
        # if requesting public videos, replace owner uid with owner username
        for video in videos:
            if "owner" in video:
                video["owner"] = auth.get_user(video["owner"]).username

    return { "base_url": BASE_URL, "videos": list(videos) }

@app.route("/video_data/<path:filename>")
def video_data(filename):
    return send_from_directory(VIDEO_FOLDER, filename)

@app.route("/v/<video_id>")
def video_player(video_id: str):
    sql = text("SELECT id, views, duration, title FROM videos WHERE id=:id")
    video = db.session.execute(sql, { "id": video_id }).mappings().fetchone()
    if not video:
        return "Not Found", 404
    
    view_count.begin_view(video_id)
    
    return render_template("player.html", 
                           header_title=SITE_NAME,
                           title=video["title"], 
                           views=video["views"],
                           video_url=f"{BASE_URL}/video_data/{video_id}/compressed.mp4",
                           thumbnail_url=f"{BASE_URL}/video_data/{video_id}/thumbnail.png")

@app.route("/v/<video_id>/view")
@auth.requires_auth()
def video_view(user: auth.User, video_id: str):
    view_count.process_view(video_id, user)
    return "OK"

@app.route("/api/setprogress/<video_id>", methods=["POST"])
# this route is only accessible to localhost, for ffmpeg to report back transcode progress
def set_progress(video_id):
    if request.remote_addr not in ["127.0.0.1", "::1"] or "X-Proxied-For" in request.headers:
        return "Forbidden", 403
    return file_upload.set_transcode_progress(video_id)