from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from src import auth, helpers

db: SQLAlchemy = None


blueprint = Blueprint('videos', __name__)

@blueprint.route("/api/video/:id", methods=["DELETE"])
@auth.requires_auth()
def delete_video(user: auth.User, id: str):
    if not is_owner(id, user):
        return helpers.create_error("You don't own this video"), 403
    
    sql = text("DELETE FROM videos WHERE id=:id")
    db.session.execute(sql, { "id": id })
    
    sql = text("DELETE FROM views WHERE video_id=:id")
    db.session.execute(sql, { "id": id })

    db.session.commit()

    return "OK"



def is_owner(video_id: str, user: auth.User):
    sql = text("SELECT * FROM videos WHERE id=:id AND owner=:user_id")
    result = db.session.execute(sql, { "id": video_id, "user_id": user.uid }).fetchone()
    return result is not None
