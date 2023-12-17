from dataclasses import dataclass
import dataclasses
import json
from time import sleep
import ffmpeg
from flask import request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import subprocess
import random
import os
from shutil import rmtree
from redis import Redis
from src.config import IS_DEV, VIDEO_FOLDER

ID_CHARACTERS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'


if not os.path.exists(VIDEO_FOLDER):
    os.mkdir(VIDEO_FOLDER)

if not IS_DEV:
    redis = Redis()
    redis.select(2)

db: SQLAlchemy = None


@dataclass
class TranscodeProgress:
    owner: int
    title: str
    duration: float
    progress: float


# dictionary from video id to transcode progress
transcode_progresses: dict[str, TranscodeProgress] = {}


def handle_upload(owner: int):
    if 'file' not in request.files:
        return create_error("Missing file in upload"), 400
    file = request.files['file']
    if not file.filename:
        return create_error("Cannot accept unnamed file"), 400

    file_extension = file.filename.rsplit('.', 1)[1]

    video_id = generate_id()

    os.mkdir(os.path.join(VIDEO_FOLDER, video_id))

    # file names only include extensions in dev env
    file_name = f"original.{file_extension}" if IS_DEV else "original"

    file_path = os.path.join(VIDEO_FOLDER, video_id, file_name)

    file.save(file_path)

    if not is_valid_video(file_path):
        cleanup_failed(video_id)
        return create_error("File is not a valid video")

    # transcode the video
    # transcoding is important, as it saves space on the server by compressing files,
    # and since the transcoded video is generated on the server, it should get rid of any trickery with the video metadata
    video_duration = transcode(owner, video_id, file_name, file.filename)

    return { "video_id": video_id, "duration": video_duration }


def cleanup_failed(video_id: str):
    path = os.path.join(VIDEO_FOLDER, video_id)
    # remove the entire folder created for the video
    if os.path.exists(path):
        rmtree(os.path.join(VIDEO_FOLDER, video_id))


def is_valid_video(file_path: str):
    try:
        # get all stream codec types in the file
        codec_types = subprocess.check_output(["ffprobe", "-show_entries", "stream=codec_type", "-of", "csv=p=0", "-v", "error", file_path], stderr=subprocess.PIPE)
        # check if there is a video stream in the file
        return b"video" in codec_types.splitlines()
    except subprocess.CalledProcessError:
        # subprocess.check_output will throw a CalledProcessError if ffprobe returns non-zero.
        # Happens if ffprobe can't process the file at all (in which case it's rejected as not a valid video)
        return False


def transcode(owner: int, video_id: str, file_name: str, title: str):
    input_video = os.path.join(VIDEO_FOLDER, video_id, file_name)
    output_video = os.path.join(VIDEO_FOLDER, video_id, "compressed.mp4")
    output_thumbnail = os.path.join(VIDEO_FOLDER, video_id, "thumbnail.png")
    output_thumbnail_lowres = os.path.join(VIDEO_FOLDER, video_id, "thumbnail-lowres.png")

    # initialize a TranscodeProgress object for this transcode
    video_duration = get_video_duration(input_video)
    transcode_progress = TranscodeProgress(owner, title, video_duration, 0)
    if IS_DEV:
        transcode_progresses[video_id] = transcode_progress
    else:
        save_transcode_progress_redis(video_id, transcode_progress)

    (  # transcode video, reporting progress to http://localhost:5000/setprogress/{video_id}
        ffmpeg.input(input_video)
        .output(output_video, maxrate="1500k", progress=f"http://localhost:5000/api/setprogress/{video_id}", movflags="faststart")
        .run_async(overwrite_output=True, quiet=True)
    )
    (  # generate thumbnail
        ffmpeg.input(input_video)
        .output(output_thumbnail, vf="thumbnail", frames=1)
        .run_async(overwrite_output=True, quiet=True)
    )
    (  # generate low resolution thumbnail
        ffmpeg.input(input_video)
        .output(output_thumbnail_lowres, vf="thumbnail", s="376x222", frames=1)
        .run(overwrite_output=True, quiet=True)
    )
    return video_duration


# ran after transcoding video
def after_transcode(video_id: str):
    try:
        sql = text("INSERT INTO videos (id, owner, title, duration, private) VALUES (:id, :owner, :title, :duration, :private)")
        if IS_DEV:
            transcode_progress = transcode_progresses[video_id]
        else:
            transcode_progress = load_transcode_progress_redis(video_id)
        duration = transcode_progress.duration
        owner = transcode_progress.owner
        title = transcode_progress.title
        db.session.execute(sql, { "id": video_id, "owner": owner, "title": title, "duration": duration, "private": False })
        db.session.commit()
    except:
        # sleep for a bit in case ffmpeg still has the file in use
        sleep(0.5)
        cleanup_failed(video_id)


def get_video_duration(file_path: str):
    try:
        return float(subprocess.check_output(["ffprobe", "-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", "-v", "error", file_path], stderr=subprocess.PIPE))
    except ValueError:
        # .mkv and some other types don't have stream duration so have to check format duration
        return float(subprocess.check_output(["ffprobe", "-select_streams", "v:0", "-show_entries", "format=duration", "-of", "csv=p=0", "-v", "error", file_path], stderr=subprocess.PIPE))


def get_transcode_progress(video_id: str):
    transcode_progress = None
    if IS_DEV:
        transcode_progress = transcode_progresses[video_id]
    else:
        transcode_progress = load_transcode_progress_redis(video_id)

    if not transcode_progress:
        return create_error(f"No progress for video: \"{video_id}\"")

    # calculate transcode progress in %
    progress = transcode_progress.progress / transcode_progress.duration * 100

    # if the progress is 100%, remove it from the transcode_progresses dict, since it's not needed anymore
    # yes I know doing like this could cause a tiny memory leak if the client never requests the progress
    if progress == 100:
        if IS_DEV:
            transcode_progresses.pop(video_id)
        else:
            redis.delete(video_id)

    return { "progress": progress }


def set_transcode_progress(video_id: str):
    # this should never happen, but just in case
    if not IS_DEV:
        transcode_progress = load_transcode_progress_redis(video_id)
    else:
        if video_id not in transcode_progresses:
            cleanup_failed(video_id)
            return "Error", 400
        transcode_progress = transcode_progresses[video_id]

    while True:
        # read one line at a time from the request stream
        # this is because ffmpeg reports progress in a single http request using a chunked transfer
        line = request.stream.readline().decode(request.content_encoding or "utf-8").strip("\n\r ")
        # if the line is len() == 0 or "progress=end", stop reading
        if len(line) == 0 or line == "progress=end":
            break

        if line.startswith("out_time_us="):
            microseconds = float(line.split("=")[1])
            transcode_progress.progress = microseconds / 1000000
            if not IS_DEV:
                save_transcode_progress_redis(video_id, transcode_progress)

    after_transcode(video_id)

    # make sure the progress ends up at 100 (in case of rounding errors, etc.)
    transcode_progress.progress = transcode_progress.duration
    if not IS_DEV:
        save_transcode_progress_redis(video_id, transcode_progress)
    return "OK", 200


def load_transcode_progress_redis(video_id: str):
    result = redis.get(video_id)
    if not result:
        return None
    return TranscodeProgress(**json.loads(result))


def save_transcode_progress_redis(video_id: str, transcode_progress: TranscodeProgress):
    redis.mset({ video_id: json.dumps(transcode_progress, cls=DataclassEncoder)})


class DataclassEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


def create_error(message: str):
    return { "error": message }


# returns True if video_id is used
def is_id_used(video_id):
    sql = text("SELECT 1 FROM videos WHERE id=:id")
    return bool(db.session.execute(sql, { "id": video_id }).fetchone())


def generate_id():
    id = ""
    # loop until an id which is not being used is found
    while not id or is_id_used(id):
        id = "".join([random.choice(ID_CHARACTERS) for i in range(5)])
    return id
