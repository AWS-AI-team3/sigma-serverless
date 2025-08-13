import boto3

import utils
import settings


rekognition = boto3.client('rekognition', region_name=settings.REGION)
s3 = boto3.client('s3', region_name=settings.REGION)


def main(event, _):
    try:
        key = utils.extract_key(event)
        utils.validate_key(key)
        utils.validate_bucket(settings.BUCKET)
        utils.validate_extension(key, settings.ALLOWED_EXTENSIONS)
        utils.verify_image_exists(s3, settings.BUCKET, key)

        data = detect_faces(key)
        return utils.respond(200, data)

    except ValueError as e:
        return utils.respond(400, message=str(e))
    except FileNotFoundError as e:
        return utils.respond(404, message=str(e))
    except RuntimeError as e:
        return utils.respond(500, message=str(e))
    except Exception as e:
        return utils.respond(500, message=f"알 수 없는 오류: {str(e)}")


def detect_faces(key):
    response = rekognition.detect_faces(Image={'S3Object': {'Bucket': settings.BUCKET, 'Name': key}}, Attributes=['DEFAULT'])

    face_count = len(response['FaceDetails'])
    is_face = face_count > 0

    return {'face_count': face_count, 'is_face': is_face}
