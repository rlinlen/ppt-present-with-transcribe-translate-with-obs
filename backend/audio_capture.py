import sounddevice as sd
import numpy as np
import asyncio
from typing import Callable
import logging

logger = logging.getLogger(__name__)

class AudioCapture:
    def __init__(self, sample_rate=16000, channels=1, chunk_size=2048):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.stream = None
        self.callback = None
        
    def start(self, callback: Callable[[bytes], None]):
        self.callback = callback
        
        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio status: {status}")
            audio_data = (indata * 32767).astype(np.int16).tobytes()
            if self.callback:
                self.callback(audio_data)
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            blocksize=self.chunk_size,
            callback=audio_callback
        )
        self.stream.start()
        logger.info(f"Audio capture started: {self.sample_rate}Hz, {self.channels} channel(s)")
    
    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            logger.info("Audio capture stopped")
