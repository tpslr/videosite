from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint, request
from sqlalchemy import text
from src import auth, helpers
from os import path
from shutil import rmtree
from src.config import VIDEO_FOLDER, BASE_URL

db: SQLAlchemy = None


blueprint = Blueprint('videos', __name__)


@blueprint.route("/api/video/<id>", methods=["DELETE"])
@auth.requires_auth()
def delete_video(user: auth.User, id: str):
    if not is_owner(id, user):
        return helpers.create_error("You don't own this video"), 403

    sql = text("DELETE FROM videos WHERE id=:id")
    db.session.execute(sql, { "id": id })

    sql = text("DELETE FROM views WHERE video_id=:id")
    db.session.execute(sql, { "id": id })

    # remove the entire folder created for the video
    video_data_path = path.join(VIDEO_FOLDER, id)
    if path.exists(video_data_path):
        rmtree(video_data_path)

    db.session.commit()

    return "OK"


class VideoUpdateAction(str, Enum):
    set_private = "set_private"
    set_public = "set_public"
    set_title = "set_title"


@blueprint.route("/api/video/<id>", methods=["PATCH"])
@auth.requires_auth()
@helpers.requires_form_data({ "action": VideoUpdateAction })
def modify_video(user: auth.User, id: str):
    if not is_owner(id, user):
        return helpers.create_error("You don't own this video"), 403

    match request.form.get("action"):
        case VideoUpdateAction.set_private:
            set_private(id, True)
        case VideoUpdateAction.set_public:
            set_private(id, False)
        case VideoUpdateAction.set_title:
            return helpers.create_error("Changing title is not implemented yet"), 501

    return "OK"


@blueprint.route("/api/video/<video_id>/comment", methods=["POST"])
@auth.requires_auth()
@helpers.requires_form_data({ "content": str })
def post_comment(user: auth.User, video_id: str):
    sql = text("INSERT INTO comments (owner, video, content) VALUES (:owner, :video, :content)")
    db.session.execute(sql, { "owner": user.uid, "video": video_id, "content": request.form.get("content") })
    db.session.commit()

    return "OK"


@blueprint.route("/api/video/<video_id>/comments")
@auth.requires_auth()
def get_comments(user: auth.User, video_id: str):
    sql = text("""SELECT U.username, C.content FROM comments C
               JOIN users U on U.uid=C.owner
               WHERE video=:video""")
    comments = db.session.execute(sql, { "video": video_id }).mappings().fetchall()
    comments = [dict(comment) for comment in comments]

    return comments


@blueprint.route("/api/videos")
@auth.requires_auth()
def list_videos(user: auth.User):
    limit = request.args["limit"] if "limit" in request.args else "20"
    offset = request.args["offset"] if "offset" in request.args else "0"
    try:
        limit = int(limit)
    except ValueError:
        return { "error": { "message": "missing arg limit" } }, 400
    try:
        offset = int(offset)
    except ValueError:
        return { "error": { "message": "missing arg offset" } }, 400

    if "public" in request.args:
        sql = text("""SELECT V.id, V.views, V.duration, V.title, U.username AS owner FROM videos V
                   JOIN users U ON U.uid=V.owner
                   WHERE V.owner!=:owner AND V.private=false
                   ORDER BY V.upload_date DESC
                   LIMIT(:limit) OFFSET(:offset*:limit);""")
    else:
        sql = text("""SELECT id, views, duration, title, private
                   FROM videos WHERE owner=:owner
                   ORDER BY upload_date DESC
                   LIMIT(:limit) OFFSET(:offset*:limit);""")
    videos = db.session.execute(sql, { "owner": user.uid, "limit": limit, "offset": offset }).mappings().fetchall()
    videos = [dict(video) for video in videos]

    return { "base_url": BASE_URL, "videos": list(videos) }


def set_private(video_id: str, private: bool):
    sql = text("UPDATE videos SET private=:private WHERE id=:id")
    db.session.execute(sql, { "id": video_id, "private": private })
    db.session.commit()


def is_owner(video_id: str, user: auth.User):
    sql = text("SELECT * FROM videos WHERE id=:id AND owner=:user_id")
    result = db.session.execute(sql, { "id": video_id, "user_id": user.uid }).fetchone()
    return result is not None
