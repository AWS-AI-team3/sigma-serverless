import json


def respond(status_code, data=None, message=None):
    body = {'message': message, 'data': data}
    return {'statusCode': status_code, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(body)}
