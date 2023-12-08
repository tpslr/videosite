# Installation

## Clone the repository
```sh
git clone https://github.com/tpslr/videosite.git
```

## Install ffmpeg
### on Ubuntu
```sh
sudo apt install ffmpeg
```
### on Windows
On windows you have to manually [download](https://ffmpeg.org/download.html) and install ffmpeg.

### Note
ffmpeg and ffprobe (included with ffmpeg) both need to be on PATH for video uploading and transcoding to work.

## Set up venv and install dependancies
```sh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Load database schema
```sh
psql -f schema.sql
```

## Set configuration in .env
Copy the following into a file named `.env`:
```env
SQLALCHEMY_DATABASE_URI="postgresql://videosite:videosite@localhost/videosite"
VIDEO_FOLDER="./video_data"
ANONYMOUS_EXPIRY_DAYS=1
FLASK_SECRET_KEY="abcdef"
ENVIRONMENT=dev
SITE_NAME="videosite"
BASE_URL="http://localhost:5000"
```
Replace values to match what you are using. I recommend keeping `ENVIRONMENT` as `dev` if you are just testing the application, since changing it to anything else will not work without ssl, and will require redis to also be installed.

For local testing you should only need to change the `SQLALCHEMY_DATABASE_URI`.

## Run the application
```sh
python -m flask run
```
I recommend running on the default port (5000), since that is currently hardcoded for the ffmpeg progress callback url.
