import json
import base64
import asyncio
import threading
import os
from io import BytesIO
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from utils import send


SAMPLE_RATE = 16000
LANGUAGE = 'ko-KR'
ENCODING = 'pcm'
BUFFER_SIZE = 3200
OVERLAP = 640

TYPE_START_TRANSCRIBE = 'start_transcribe'
TYPE_SEND_AUDIO = 'send_audio'
TYPE_STOP_TRANSCRIBE = 'stop_transcribe'
TYPE_TRANSCRIBE_STARTED = 'transcribe_started'
TYPE_TRANSCRIBE_STOPPED = 'transcribe_stopped'
TYPE_TRANSCRIPT = 'transcript'
TYPE_ERROR = 'error'

region = os.environ.get('REGION')
vocabulary = os.environ.get('VOCABULARY')
transcribe_client = TranscribeStreamingClient(region=region)

connections = {}


class ConnectionState:
    def __init__(self):
        self.buffer = BytesIO()
        self.audio_queue = []
        self.is_active = False
        self.total_chunks = 0


class TranscriptHandler(TranscriptResultStreamHandler):
    def __init__(self, connection_id, event):
        self.connection_id = connection_id
        self.event = event
        self.last_partial = ""

    async def handle_transcript_event(self, event: TranscriptEvent):
        try:
            results = event.transcript.results
            for result in results:
                if result.alternatives:
                    raw = result.alternatives[0].transcript
                    text = clean_text(raw)

                    if not text:
                        continue

                    if result.is_partial and text == self.last_partial:
                        continue

                    if result.is_partial:
                        self.last_partial = text
                    else:
                        self.last_partial = ""

                    confidence = 0
                    if hasattr(result.alternatives[0], 'items') and result.alternatives[0].items:
                        confs = [
                            float(item.confidence)
                            for item in result.alternatives[0].items
                            if hasattr(item, 'confidence') and item.confidence is not None
                        ]
                        confidence = sum(confs) / len(confs) if confs else 0

                    data = {'text': text, 'is_partial': result.is_partial, 'confidence': round(confidence, 2) if confidence > 0 else None}

                    await send(self.connection_id, TYPE_TRANSCRIPT, data=data, event=self.event)

        except Exception as e:
            await send(self.connection_id, TYPE_ERROR, data={'message': f'Recognition error: {str(e)}'}, event=self.event)


def main(event, context):
    try:
        connection_id = extract_connection_id(event)
        message = extract_message(event)
        type = extract_type(message)

        if type == TYPE_START_TRANSCRIBE:
            start_transcription(connection_id, event)
            asyncio.run(send(connection_id, TYPE_TRANSCRIBE_STARTED, data={'message': 'Recognition started'}, event=event))

        elif type == TYPE_SEND_AUDIO:
            process_audio_message(connection_id, message)

        elif type == TYPE_STOP_TRANSCRIBE:
            stop_transcription(connection_id)
            asyncio.run(send(connection_id, TYPE_TRANSCRIBE_STOPPED, data={'message': 'Recognition stopped'}, event=event))

        return {"statusCode": 200}

    except ValueError as e:
        return {"statusCode": 400}
    except Exception as e:
        return {"statusCode": 500}


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


def process_audio_message(connection_id, message):
    if 'data' in message and connection_id in connections:
        try:
            audio_data = base64.b64decode(message['data'])
            chunk = process_audio_chunk(connection_id, audio_data)

            if chunk and connections[connection_id].is_active:
                connections[connection_id].audio_queue.append(chunk)

        except Exception:
            pass


def process_audio_chunk(connection_id, data):
    if connection_id not in connections:
        return None

    state = connections[connection_id]
    state.buffer.write(data)

    if state.buffer.tell() >= BUFFER_SIZE:
        state.buffer.seek(0)
        chunk = state.buffer.read()

        state.buffer = BytesIO()
        if len(chunk) > OVERLAP:
            state.buffer.write(chunk[-OVERLAP:])

        state.total_chunks += 1
        return chunk

    return None


def start_transcription(connection_id, event):
    if connection_id not in connections:
        connections[connection_id] = ConnectionState()

    connections[connection_id].is_active = True
    connections[connection_id].audio_queue = []

    thread = threading.Thread(target=run_transcription, args=(connection_id, event), daemon=True)
    thread.start()


def run_transcription(connection_id, event):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(transcribe_stream(connection_id, event))
    loop.close()


async def transcribe_stream(connection_id, event):
    if connection_id not in connections:
        return

    state = connections[connection_id]

    try:
        stream = await transcribe_client.start_stream_transcription(
            language_code=LANGUAGE,
            media_sample_rate_hz=SAMPLE_RATE,
            media_encoding=ENCODING,
            vocabulary_name=vocabulary,
            enable_partial_results_stabilization=True,
            partial_results_stability="low",
        )

        handler = TranscriptHandler(connection_id, event)

        async def send_audio():
            while state.is_active:
                if state.audio_queue:
                    chunk = state.audio_queue.pop(0)
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
                else:
                    await asyncio.sleep(0.01)
            await stream.input_stream.end_stream()

        async def receive_transcripts():
            async for event in stream.output_stream:
                if not state.is_active:
                    break
                await handler.handle_transcript_event(event)

        await asyncio.gather(send_audio(), receive_transcripts())

    except Exception as e:
        await send(connection_id, TYPE_ERROR, data={'message': f'Recognition error: {str(e)}'}, event=event)
    finally:
        cleanup_connection(connection_id)


def stop_transcription(connection_id):
    if connection_id in connections:
        connections[connection_id].is_active = False


def cleanup_connection(connection_id):
    if connection_id in connections:
        connections[connection_id].is_active = False
        del connections[connection_id]
