import json


def respond(status_code, data=None, message=None):
    body = {'message': message, 'data': data}
    return {'statusCode': status_code, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(body)}


def extract_key(event):
    body = json.loads(event['body']) if event.get('body') else {}
    return body.get('key')


def validate_key(key):
    if not key:
        raise ValueError("'key' 파라미터가 필요합니다")


def validate_bucket(bucket):
    if not bucket:
        raise ValueError("버킷이 설정되지 않았습니다")


def validate_extension(key, allowed_extensions):
    if not any(key.lower().endswith(ext) for ext in allowed_extensions):
        raise ValueError("잘못된 파일 확장자입니다. jpg, jpeg만 허용됩니다")


def verify_image_exists(s3_client, bucket, key):
    from botocore.exceptions import ClientError

    try:
        s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response['Error']['Code'] == '403':
            raise FileNotFoundError(f"이미지를 찾을 수 없습니다 (bucket: {bucket}, key: {key})")
        else:
            raise RuntimeError(f"S3 접근 오류: {str(e)}")
