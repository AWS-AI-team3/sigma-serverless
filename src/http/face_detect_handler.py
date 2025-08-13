import json
import os
import boto3
from utils import respond


ALLOWED_EXTENSIONS = ['.jpg', '.jpeg']

region = os.environ.get('REGION')
bucket = os.environ.get('USER_FACE_BUCKET')

rekognition = boto3.client('rekognition', region_name=region)
s3 = boto3.client('s3', region_name=region)


def main(event, context):
    try:
        key = extract_key(event)
        validate_key(key)
        validate_bucket()
        validate_extension(key)
        verify_image_exists(key)

        data = detect_faces(key)
        return respond(200, data)

    except ValueError as e:
        return respond(400, message=str(e))
    except FileNotFoundError as e:
        return respond(404, message=str(e))
    except RuntimeError as e:
        return respond(500, message=str(e))
    except Exception as e:
        return respond(500, message=f"알 수 없는 오류: {str(e)}")


def extract_key(event):
    body = json.loads(event['body']) if event.get('body') else {}
    return body.get('key')


def validate_key(key):
    if not key:
        raise ValueError("'key' 파라미터가 필요합니다")


def validate_bucket():
    if not bucket:
        raise ValueError("버킷이 설정되지 않았습니다")


def validate_extension(key):
    if not any(key.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValueError("잘못된 파일 확장자입니다. jpg, jpeg만 허용됩니다")


def verify_image_exists(key):
    from botocore.exceptions import ClientError

    try:
        s3.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response['Error']['Code'] == '403':
            raise FileNotFoundError(f"이미지를 찾을 수 없습니다 (bucket: {bucket}, key: {key})")
        else:
            raise RuntimeError(f"S3 접근 오류: {str(e)}")


def detect_faces(key):
    response = rekognition.detect_faces(Image={'S3Object': {'Bucket': bucket, 'Name': key}}, Attributes=['DEFAULT'])

    face_count = len(response['FaceDetails'])
    is_face = face_count > 0

    return {'face_count': face_count, 'is_face': is_face}
