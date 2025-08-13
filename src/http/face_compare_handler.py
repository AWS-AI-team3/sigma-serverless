import json
import os
import boto3
from utils import respond


ALLOWED_EXTENSIONS = ['.jpg', '.jpeg']
SIMILARITY_THRESHOLD = 80.0

region = os.environ.get('REGION')
bucket = os.environ.get('USER_FACE_BUCKET')

rekognition = boto3.client('rekognition', region_name=region)
s3 = boto3.client('s3', region_name=region)


def main(event, context):
    try:
        key1, key2 = extract_keys(event)
        validate_keys(key1, key2)
        validate_bucket()
        validate_extensions(key1, key2)
        verify_images_exist(key1, key2)

        comparison_data = compare_faces(key1, key2)
        return respond(200, comparison_data)

    except ValueError as e:
        return respond(400, message=str(e))
    except FileNotFoundError as e:
        return respond(404, message=str(e))
    except RuntimeError as e:
        return respond(500, message=str(e))
    except Exception as e:
        return respond(500, message=f"알 수 없는 오류: {str(e)}")


def extract_keys(event):
    body = json.loads(event['body']) if event.get('body') else {}
    return body.get('key1'), body.get('key2')


def validate_keys(key1, key2):
    if not key1:
        raise ValueError("'key1' 파라미터가 필요합니다")
    if not key2:
        raise ValueError("'key2' 파라미터가 필요합니다")


def validate_bucket():
    if not bucket:
        raise ValueError("버킷이 설정되지 않았습니다")


def validate_extensions(key1, key2):
    if not any(key1.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValueError("key1: 잘못된 파일 확장자입니다. jpg, jpeg만 허용됩니다")
    if not any(key2.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValueError("key2: 잘못된 파일 확장자입니다. jpg, jpeg만 허용됩니다")


def verify_images_exist(key1, key2):
    from botocore.exceptions import ClientError

    try:
        s3.head_object(Bucket=bucket, Key=key1)
    except ClientError as e:
        if e.response['Error']['Code'] == '403':
            raise FileNotFoundError(f"첫 번째 이미지를 찾을 수 없습니다: {key1}")
        else:
            raise RuntimeError(f"첫 번째 이미지 S3 접근 오류: {str(e)}")

    try:
        s3.head_object(Bucket=bucket, Key=key2)
    except ClientError as e:
        if e.response['Error']['Code'] == '403':
            raise FileNotFoundError(f"두 번째 이미지를 찾을 수 없습니다: {key2}")
        else:
            raise RuntimeError(f"두 번째 이미지 S3 접근 오류: {str(e)}")


def compare_faces(key1, key2):
    response = rekognition.compare_faces(
        SourceImage={'S3Object': {'Bucket': bucket, 'Name': key1}},
        TargetImage={'S3Object': {'Bucket': bucket, 'Name': key2}},
        SimilarityThreshold=0,
    )

    if not response['FaceMatches']:
        similarity = 0.0
        is_same = False
    else:
        similarity = response['FaceMatches'][0]['Similarity']
        is_same = similarity >= SIMILARITY_THRESHOLD

    return {'similarity': round(similarity, 2), 'is_same': is_same}
