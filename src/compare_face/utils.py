import json


def respond(status_code, data=None, message=None):
    body = {'message': message, 'data': data}
    return {'statusCode': status_code, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(body)}


def extract_keys(event):
    body = json.loads(event['body']) if event.get('body') else {}
    return body.get('key1'), body.get('key2')


def validate_keys(key1, key2):
    if not key1:
        raise ValueError("'key1' 파라미터가 필요합니다")
    if not key2:
        raise ValueError("'key2' 파라미터가 필요합니다")


def validate_bucket(bucket):
    if not bucket:
        raise ValueError("버킷이 설정되지 않았습니다")


def validate_extensions(key1, key2, allowed_extensions):
    if not any(key1.lower().endswith(ext) for ext in allowed_extensions):
        raise ValueError("key1: 잘못된 파일 확장자입니다. jpg, jpeg만 허용됩니다")
    if not any(key2.lower().endswith(ext) for ext in allowed_extensions):
        raise ValueError("key2: 잘못된 파일 확장자입니다. jpg, jpeg만 허용됩니다")


def verify_images_exist(s3_client, bucket, key1, key2):
    from botocore.exceptions import ClientError

    try:
        s3_client.head_object(Bucket=bucket, Key=key1)
    except ClientError as e:
        if e.response['Error']['Code'] == '403':
            raise FileNotFoundError(f"첫 번째 이미지를 찾을 수 없습니다: {key1}")
        else:
            raise RuntimeError(f"첫 번째 이미지 S3 접근 오류: {str(e)}")

    try:
        s3_client.head_object(Bucket=bucket, Key=key2)
    except ClientError as e:
        if e.response['Error']['Code'] == '403':
            raise FileNotFoundError(f"두 번째 이미지를 찾을 수 없습니다: {key2}")
        else:
            raise RuntimeError(f"두 번째 이미지 S3 접근 오류: {str(e)}")
