import boto3

import utils
import settings


rekognition = boto3.client('rekognition', region_name=settings.REGION)
s3 = boto3.client('s3', region_name=settings.REGION)


def main(event, context):
    try:
        key1, key2 = utils.extract_keys(event)
        utils.validate_keys(key1, key2)
        utils.validate_bucket(settings.BUCKET)
        utils.validate_extensions(key1, key2, settings.ALLOWED_EXTENSIONS)
        utils.verify_images_exist(s3, settings.BUCKET, key1, key2)

        comparison_data = compare_faces(key1, key2)
        return utils.respond(200, comparison_data)

    except ValueError as e:
        return utils.respond(400, message=str(e))
    except FileNotFoundError as e:
        return utils.respond(404, message=str(e))
    except RuntimeError as e:
        return utils.respond(500, message=str(e))
    except Exception as e:
        return utils.respond(500, message=f"알 수 없는 오류: {str(e)}")


def compare_faces(key1, key2):
    response = rekognition.compare_faces(
        SourceImage={'S3Object': {'Bucket': settings.BUCKET, 'Name': key1}},
        TargetImage={'S3Object': {'Bucket': settings.BUCKET, 'Name': key2}},
        SimilarityThreshold=0,
    )

    if not response['FaceMatches']:
        similarity = 0.0
        is_same = False
    else:
        similarity = response['FaceMatches'][0]['Similarity']
        is_same = similarity >= settings.SIMILARITY_THRESHOLD

    return {'similarity': round(similarity, 2), 'is_same': is_same}
