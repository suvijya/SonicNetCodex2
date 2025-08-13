"""
GGWave audio sender using pyggwave.
"""
import asyncio
import logging
import pyaudio
import pyggwave
from .base_transport import BaseSender
from config import GGWAVE_SAMPLE_RATE, GGWAVE_SAMPLES_PER_FRAME, GGWAVE_VOLUME

logger = logging.getLogger(__name__)

class GGWaveSender(BaseSender):
    def __init__(self):
        self.pyaudio_instance = None
        self.output_stream = None
        self.ggwave_instance = None
        self.running = False

    async def start(self):
        logger.info("Starting GGWave sender...")
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.ggwave_instance = pyggwave.GGWave()
            self.output_stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=GGWAVE_SAMPLE_RATE,
                output=True,
                frames_per_buffer=GGWAVE_SAMPLES_PER_FRAME
            )
            self.running = True
            logger.info("GGWave sender started successfully.")
        except Exception as e:
            logger.error(f"Failed to start GGWave sender: {e}")
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
            self.pyaudio_instance = None

    async def stop(self):
        if not self.running:
            return
        logger.info("Stopping GGWave sender...")
        self.running = False
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        if self.ggwave_instance:
            self.ggwave_instance.free()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
        logger.info("GGWave sender stopped.")

    async def send(self, data: bytes):
        if not self.running or not self.output_stream:
            logger.warning("GGWave sender not running, cannot send.")
            return
        try:
            waveform = self.ggwave_instance.encode(
                data,
                protocol=pyggwave.Protocol.ULTRASOUND_FAST,
                volume=int(GGWAVE_VOLUME)
            )
            if waveform:
                self.output_stream.write(waveform)
                logger.debug(f"Sent {len(data)} bytes via GGWave.")
            else:
                logger.error("Failed to encode data for GGWave.")
        except Exception as e:
            logger.error(f"Error sending data via GGWave: {e}")

