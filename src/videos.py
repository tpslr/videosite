from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from src import auth, helpers
from os import environ, path
from shutil import rmtree
from src.file_upload import VIDEO_FOLDER

db: SQLAlchemy = None

BASE_URL = environ.get("BASE_URL") or "http://localhost:5000"

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


@blueprint.route("/api/videos")
@auth.requires_auth()
def list_videos(user: auth.User):
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
        sql = text("SELECT id, views, duration, title, owner FROM videos WHERE owner!=:owner AND private=false ORDER BY upload_date DESC LIMIT(:limit) OFFSET(:offset*:limit);")
    else:
        sql = text("SELECT id, views, duration, title, private FROM videos WHERE owner=:owner ORDER BY upload_date DESC LIMIT(:limit) OFFSET(:offset*:limit);")
    videos = db.session.execute(sql, { "owner": user.uid, "limit": limit, "offset": offset }).mappings().fetchall()
    videos = [dict(video) for video in videos]

    if "public" in request.args:
        # if requesting public videos, replace owner uid with owner username
        for video in videos:
            if "owner" in video:
                video["owner"] = auth.get_user(video["owner"]).username

    return { "base_url": BASE_URL, "videos": list(videos) }


def set_private(video_id: str, private: bool):
    sql = text("UPDATE videos SET private=:private WHERE id=:id")
    db.session.execute(sql, { "id": video_id, "private": private })
    db.session.commit()


def is_owner(video_id: str, user: auth.User):
    sql = text("SELECT * FROM videos WHERE id=:id AND owner=:user_id")
    result = db.session.execute(sql, { "id": video_id, "user_id": user.uid }).fetchone()
    return result is not None
