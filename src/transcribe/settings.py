import os


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

REGION = os.environ.get('REGION')
VOCABULARY = os.environ.get('VOCABULARY')
