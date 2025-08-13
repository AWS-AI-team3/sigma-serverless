import os


ALLOWED_EXTENSIONS = ['.jpg', '.jpeg']
SIMILARITY_THRESHOLD = 80.0

REGION = os.environ.get('REGION')
BUCKET = os.environ.get('USER_FACE_BUCKET')
