from src import config
from flask import Flask, request, make_response, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from src import file_upload, auth, view_count, helpers, videos
from src.config import SITE_NAME, BASE_URL, VIDEO_FOLDER, IS_DEV


app = Flask(SITE_NAME)

config.set_config(app)


db = SQLAlchemy(app)

auth.db = db
file_upload.db = db
view_count.db = db
videos.db = db


app.register_blueprint(videos.blueprint)


@app.route("/")
def index():
    return render_template("index.html", header_title=SITE_NAME, title=SITE_NAME)


@app.route("/login")
def login_page():
    return render_template("login.html", header_title=SITE_NAME, title=f"Login - {SITE_NAME}", site_name=SITE_NAME)


@app.route("/signup")
def signup_page():
    return render_template("login.html", header_title=SITE_NAME, title=f"Sign Up - {SITE_NAME}", site_name=SITE_NAME)


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
    refresh_token = request.headers.get("Authorization")
    if refresh_token:
        refresh = auth.convert_anonymous_user(request.form["username"], request.form["password"], refresh_token)
    else:
        refresh = auth.create_normal_user(request.form["username"], request.form["password"])

    if type(refresh) is auth.AuthError:
        return { "error": refresh }

    return { "refresh": refresh }


@app.route("/api/logout", methods=["POST"])
@auth.requires_auth()
def logout(user: auth.User):
    return auth.logout(user, request.headers.get("Authorization"))


@app.route("/api/upload", methods=["POST"])
@auth.requires_auth()
def upload(user: auth.User):
    return file_upload.handle_upload(user.uid)


@app.route("/api/progress/<video_id>")
def progress(video_id):
    return file_upload.get_transcode_progress(video_id)


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
