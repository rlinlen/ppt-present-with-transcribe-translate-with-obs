import asyncio
import os
import boto3
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
import logging

logger = logging.getLogger(__name__)

def get_translate_client():
    return boto3.client(
        'translate',
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

class TranscribeHandler(TranscriptResultStreamHandler):
    def __init__(self, output_stream, callback):
        super().__init__(output_stream)
        self.callback = callback
        self.translate_client = get_translate_client()
        
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if result.alternatives:
                transcript = result.alternatives[0].transcript
                is_partial = result.is_partial
                
                detected_language = 'en'
                if hasattr(result, 'language_code'):
                    detected_language = result.language_code
                
                # Translate if there's text
                translation = ''
                if transcript.strip():
                    try:
                        # Determine target language
                        if detected_language.startswith('en'):
                            source_code = 'en'
                            target_code = 'zh-TW'
                        else:
                            source_code = 'zh-TW'
                            target_code = 'en'
                        
                        response = self.translate_client.translate_text(
                            Text=transcript,
                            SourceLanguageCode=source_code,
                            TargetLanguageCode=target_code
                        )
                        translation = response.get('TranslatedText', '')
                    except Exception as e:
                        logger.error(f"Translation error: {e}")
                
                await self.callback({
                    'transcript': transcript,
                    'translation': translation,
                    'is_partial': is_partial,
                    'language_code': detected_language
                })

class TranscribeClient:
    def __init__(self, region=None):
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.client = None
        self.stream = None
        
    async def start_stream(self, callback, language_options=['en-US', 'zh-TW']):
        self.client = TranscribeStreamingClient(region=self.region)
        
        stream_params = {
            'language_code': None,
            'media_sample_rate_hz': 16000,
            'media_encoding': 'pcm',
            'identify_multiple_languages': True,
            'language_options': language_options,
            'enable_partial_results_stabilization': True,
            'partial_results_stability': 'high'
        }
        
        self.stream = await self.client.start_stream_transcription(**stream_params)
        
        handler = TranscribeHandler(self.stream.output_stream, callback)
        await asyncio.gather(handler.handle_events())
        
    async def send_audio(self, audio_chunk: bytes):
        if self.stream:
            await self.stream.input_stream.send_audio_event(audio_chunk=audio_chunk)
    
    async def stop(self):
        if self.stream:
            await self.stream.input_stream.end_stream()
            logger.info("Transcribe stream stopped")
