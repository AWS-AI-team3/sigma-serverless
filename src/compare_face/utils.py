import json
from botocore.exceptions import ClientError


def respond(status_code, data=None, message=None):
    body = {'message': message, 'data': data}
    return {'statusCode': status_code, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(body)}


def extract_keys(event):
    body = json.loads(event['body']) if event.get('body') else {}
    return body.get('key1'), body.get('key2')


def validate_keys(s3_client, bucket, key1, key2):
    if not key1:
        raise ValueError("'key1' 파라미터가 필요합니다")

    if not key2:
        raise ValueError("'key2' 파라미터가 필요합니다")

    try:
        s3_client.head_object(Bucket=bucket, Key=key1)
    except ClientError as e:
        if e.response['Error']['Code'] == '403':
            raise FileNotFoundError(f"이미지를 찾을 수 없습니다 (bucket: {bucket}, key: {key1})")
        else:
            raise RuntimeError(f"S3 접근 오류: {str(e)}")

    try:
        s3_client.head_object(Bucket=bucket, Key=key2)
    except ClientError as e:
        if e.response['Error']['Code'] == '403':
            raise FileNotFoundError(f"이미지를 찾을 수 없습니다 (bucket: {bucket}, key: {key2})")
        else:
            raise RuntimeError(f"S3 접근 오류: {str(e)}")

    return


def validate_bucket(bucket):
    if not bucket:
        raise ValueError("버킷이 설정되지 않았습니다")


def find_image(s3_client, bucket, key):
    from botocore.exceptions import ClientError

    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return key
    except ClientError as e:
        if e.response['Error']['Code'] == '403':
            raise FileNotFoundError(f"이미지를 찾을 수 없습니다 (bucket: {bucket}, key: {key})")
        else:
            raise RuntimeError(f"S3 접근 오류: {str(e)}")
