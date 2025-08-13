import os


ALLOWED_EXTENSIONS = ['.jpg', '.jpeg']

REGION = os.environ.get('REGION')
BUCKET = os.environ.get('USER_FACE_BUCKET')
