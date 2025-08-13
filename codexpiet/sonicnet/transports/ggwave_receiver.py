"""
GGWave audio receiver using pyggwave.
"""
import asyncio
import logging
import pyaudio
import pyggwave
import numpy as np
from .base_transport import BaseReceiver
from config import GGWAVE_SAMPLE_RATE, GGWAVE_SAMPLES_PER_FRAME
from packet import SOSPacket

logger = logging.getLogger(__name__)

class GGWaveReceiver(BaseReceiver):
    def __init__(self, message_queue: asyncio.Queue):
        super().__init__(message_queue)
        self.pyaudio_instance = None
        self.input_stream = None
        self.ggwave_instance = None
        self.running = False
        self._receive_task = None

    async def start(self):
        logger.info("Starting GGWave receiver...")
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.ggwave_instance = pyggwave.GGWave()
            self.input_stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=GGWAVE_SAMPLE_RATE,
                input=True,
                frames_per_buffer=GGWAVE_SAMPLES_PER_FRAME,
            )
            self.running = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            logger.info("GGWave receiver started successfully.")
        except Exception as e:
            logger.error(f"Failed to start GGWave receiver: {e}")
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
            self.pyaudio_instance = None

    async def stop(self):
        if not self.running:
            return
        logger.info("Stopping GGWave receiver...")
        self.running = False
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.ggwave_instance:
            self.ggwave_instance.free()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
        logger.info("GGWave receiver stopped.")

    async def _receive_loop(self):
        """Continuously listen for and process audio data."""
        loop = asyncio.get_running_loop()
        while self.running:
            try:
                # Run the blocking read operation in a separate thread
                data = await loop.run_in_executor(
                    None, self.input_stream.read, GGWAVE_SAMPLES_PER_FRAME, False
                )

                audio_data = np.frombuffer(data, dtype=np.float32)
                decoded_text = self.ggwave_instance.decode(audio_data)

                if decoded_text:
                    logger.debug(f"GGWave received: {decoded_text}")
                    try:
                        # The packet is expected to be in JSON format
                        packet = SOSPacket.from_json(decoded_text)
                        await self.message_queue.put(packet)
                    except Exception as e:
                        logger.error(f"Error processing received ggwave data: {e}")
            except Exception as e:
                logger.error(f"Error in GGWave receive loop: {e}")
                # Avoid busy-looping on error
                await asyncio.sleep(0.1)
