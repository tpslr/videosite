from flask import session, request
from uuid import uuid4
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
from .auth import User

db: SQLAlchemy = None


def begin_view(video_id: str):
    view_id = uuid4()

    view = { "v": video_id, "h": view_id, "w": False, "t": datetime.now().timestamp() }

    session["v"] = view


def process_view(video_id: str, user: User):
    if "v" not in session:
        return
    view = session["v"]

    # if this is the first request, ignore
    if not view["w"]:
        view["w"] = True
        session.update(v=view)
        return
    
    # if time from begin_view is less than 10 seconds, ignore
    if view["t"] > datetime.now().timestamp() - 10:
        return
    
    # if view time missing from request headers, ignore
    if "T" not in request.headers:
        return
    
    try:
        # if view time is less than 5, ignore
        if float(request.headers["T"]) < 5:
            return
    except ValueError:
        return
    
    try:
        sql = text("SELECT count FROM views WHERE video_id=:video_id AND user_id=:user_id;")
        response = db.session.execute(sql, { "video_id": video_id, "user_id": user.uid }).fetchone()

        if not response:
            # user hasn't viewed the video before
            sql = text("INSERT INTO views (video_id, user_id, count) VALUES (:video_id, :user_id, 0);")
            db.session.execute(sql, { "video_id": video_id, "user_id": user.uid })
            sql = text("UPDATE videos SET views=views+1 WHERE id=:video_id;")
            db.session.execute(sql, { "video_id": video_id, })
        else:
            # user has viewed the video before
            sql = text("UPDATE views SET count=count+1 WHERE video_id=:video_id AND user_id=:user_id;")
            db.session.execute(sql, { "video_id": video_id, "user_id": user.uid })
        
        db.session.commit()

        # remove view from session
        session.pop("v")
    except Exception as e:
        print(e)
