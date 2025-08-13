import json
import boto3


def send(connection_id, type, event, data=None):
    domain = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    client = boto3.client('apigatewaymanagementapi', endpoint_url=f"https://{domain}/{stage}")

    message = {'type': type}
    if data:
        message.update(data)
    client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(message, ensure_ascii=False).encode('utf-8'))


def extract_connection_id(event):
    return event['requestContext']['connectionId']


def extract_message(event):
    if not event.get('body'):
        raise ValueError("메시지가 필요합니다")
    return json.loads(event['body'])


def extract_type(message):
    return message.get('type', '')


def clean_text(text):
    return text.replace('.', '').strip()
