import json
import boto3


async def send(connection_id, type, event, data=None):
    domain = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    client = boto3.client('apigatewaymanagementapi', endpoint_url=f"https://{domain}/{stage}")

    message = {'type': type}
    if data:
        message.update(data)
    client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(message, ensure_ascii=False).encode('utf-8'))
