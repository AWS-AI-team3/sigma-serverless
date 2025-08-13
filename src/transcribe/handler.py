import base64
import asyncio
import threading
from io import BytesIO
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

import utils
import settings


transcribe_client = TranscribeStreamingClient(region=settings.REGION)

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
                    text = utils.clean_text(raw)

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

                    data = {
                        'text': text,
                        'is_partial': result.is_partial,
                        'confidence': (round(confidence, 2) if confidence > 0 else None),
                    }

                    utils.send(
                        self.connection_id,
                        settings.TYPE_TRANSCRIPT,
                        self.event,
                        data=data,
                    )

        except Exception as e:
            utils.send(
                self.connection_id,
                settings.TYPE_ERROR,
                self.event,
                data={'message': f'Recognition error: {str(e)}'},
            )


def main(event, context):
    try:
        connection_id = utils.extract_connection_id(event)
        message = utils.extract_message(event)
        type = utils.extract_type(message)

        if type == settings.TYPE_START_TRANSCRIBE:
            start_transcription(connection_id, event)
            utils.send(connection_id, settings.TYPE_TRANSCRIBE_STARTED, event)

        elif type == settings.TYPE_SEND_AUDIO:
            process_audio_message(connection_id, message)

        elif type == settings.TYPE_STOP_TRANSCRIBE:
            stop_transcription(connection_id)
            utils.send(connection_id, settings.TYPE_TRANSCRIBE_STOPPED, event)

        return {"statusCode": 200}

    except ValueError as e:
        return {"statusCode": 400}
    except Exception as e:
        return {"statusCode": 500}


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

    if state.buffer.tell() >= settings.BUFFER_SIZE:
        state.buffer.seek(0)
        chunk = state.buffer.read()

        state.buffer = BytesIO()
        if len(chunk) > settings.OVERLAP:
            state.buffer.write(chunk[-settings.OVERLAP :])

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
            language_code=settings.LANGUAGE,
            media_sample_rate_hz=settings.SAMPLE_RATE,
            media_encoding=settings.ENCODING,
            vocabulary_name=settings.VOCABULARY,
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
        utils.send(
            connection_id,
            settings.TYPE_ERROR,
            event,
            data={'message': f'Recognition error: {str(e)}'},
        )
    finally:
        cleanup_connection(connection_id)


def stop_transcription(connection_id):
    if connection_id in connections:
        connections[connection_id].is_active = False


def cleanup_connection(connection_id):
    if connection_id in connections:
        connections[connection_id].is_active = False
        del connections[connection_id]
