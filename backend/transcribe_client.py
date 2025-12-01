import asyncio
import os
import boto3
import time
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
        self.pending_translations = 0
        self.is_active = True
        self.last_translation_time = 0
        self.partial_count = 0
        self.audio_received_time = time.time()
        
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        if not self.is_active:
            return
        
        transcribe_received_time = time.time()
        transcribe_latency = transcribe_received_time - self.audio_received_time
        logger.info(f"Transcribe latency: {transcribe_latency:.2f}s")
            
        results = transcript_event.transcript.results
        for result in results:
            if result.alternatives:
                transcript = result.alternatives[0].transcript
                is_partial = result.is_partial
                
                detected_language = 'en'
                if hasattr(result, 'language_code'):
                    detected_language = result.language_code
                
                # Decide if we should translate
                should_translate = False
                if not is_partial:
                    # Always translate final results
                    should_translate = True
                    self.partial_count = 0
                else:
                    # For partials: translate every 3rd result OR every 0.5 second
                    self.partial_count += 1
                    current_time = time.time()
                    if self.partial_count >= 3 or (current_time - self.last_translation_time) >= 0.5:
                        should_translate = True
                        self.partial_count = 0
                        self.last_translation_time = current_time
                
                # Translate if there's text
                translation = ''
                translation_start = time.time()
                if transcript.strip() and self.is_active and should_translate:
                    try:
                        # Determine target language
                        if detected_language.startswith('en'):
                            source_code = 'en'
                            target_code = 'zh-TW'
                        else:
                            source_code = 'zh-TW'
                            target_code = 'en'
                        
                        self.pending_translations += 1
                        if self.pending_translations > 3:
                            logger.warning(f"Translation queue: {self.pending_translations} pending (partial={is_partial})")
                        
                        response = self.translate_client.translate_text(
                            Text=transcript,
                            SourceLanguageCode=source_code,
                            TargetLanguageCode=target_code
                        )
                        translation = response.get('TranslatedText', '')
                        
                        translation_latency = time.time() - translation_start
                        logger.info(f"Translation latency: {translation_latency:.2f}s")
                        
                        self.pending_translations -= 1
                        if self.pending_translations > 3:
                            logger.warning(f"Translation completed. Queue: {self.pending_translations} pending")
                        
                    except Exception as e:
                        self.pending_translations -= 1
                        logger.error(f"Translation error: {e}")
                
                total_latency = time.time() - self.audio_received_time
                logger.info(f"Total latency (audio->display): {total_latency:.2f}s (partial={is_partial})")
                
                if self.is_active:
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
        self.handler = None
        
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
        
        self.handler = TranscribeHandler(self.stream.output_stream, callback)
        await asyncio.gather(self.handler.handle_events())
        
    async def send_audio(self, audio_chunk: bytes):
        if self.stream:
            if self.handler:
                self.handler.audio_received_time = time.time()
            await self.stream.input_stream.send_audio_event(audio_chunk=audio_chunk)
    
    async def stop(self):
        if self.handler:
            self.handler.is_active = False
        if self.stream:
            await self.stream.input_stream.end_stream()
            logger.info("Transcribe stream stopped")
