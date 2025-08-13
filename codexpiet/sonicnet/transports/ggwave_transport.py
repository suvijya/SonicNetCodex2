"""
Enhanced GGWave transport for sending and receiving data over audio.
Refactored with separate sender and receiver components.
"""

import asyncio
import logging
import json
import time
import queue
from typing import Optional, Dict, Any

from .base_transport import BaseTransportSender, BaseTransportReceiver, BaseTransportManager
from packet import SOSPacket
from config import GGWAVE_SAMPLE_RATE, GGWAVE_SAMPLES_PER_FRAME, GGWAVE_VOLUME

try:
    import pyaudio
    import pyggwave
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

logger = logging.getLogger(__name__)

class GGWaveSender(BaseTransportSender):
    """Handles sending SOS packets over audio using GGWave."""

    def __init__(self, node_id: str):
        super().__init__(node_id)
        self.pyaudio_instance = None
        self.ggwave_instance = None
        self.output_stream = None
        self.sample_rate = GGWAVE_SAMPLE_RATE
        self.samples_per_frame = GGWAVE_SAMPLES_PER_FRAME
        self.volume = int(GGWAVE_VOLUME)

    async def start(self):
        """Initialize and start the GGWave sender."""
        if not AUDIO_AVAILABLE:
            logger.warning("GGWave sender unavailable. Audio libraries not installed.")
            return False

        try:
            # Initialize PyAudio
            self.pyaudio_instance = pyaudio.PyAudio()

            # Initialize GGWave
            self.ggwave_instance = pyggwave.GGWave()

            # Set up audio output stream
            self.output_stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.samples_per_frame
            )

            self.running = True
            logger.info(f"GGWave sender started for node {self.node_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start GGWave sender: {e}")
            self.stats['send_errors'] += 1
            return False

    async def stop(self):
        """Stop the GGWave sender."""
        self.running = False

        # Close the output stream
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except Exception as e:
                logger.error(f"Error closing GGWave output stream: {e}")

        # Free the GGWave instance
        if self.ggwave_instance:
            try:
                self.ggwave_instance.free()
            except Exception as e:
                logger.error(f"Error freeing GGWave instance: {e}")

        # Terminate PyAudio
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")

        logger.info("GGWave sender stopped")

    async def send(self, packet: SOSPacket):
        """Send a packet via audio using GGWave."""
        if not self.running or not self.ggwave_instance or not self.output_stream:
            return False

        try:
            # Ensure sender ID is set
            if not packet.sender_id:
                packet.sender_id = self.node_id

            # Prepare packet data
            packet_data = packet.to_json()

            # Generate audio waveform
            waveform = self.ggwave_instance.encode(
                packet_data,
                protocol=pyggwave.Protocol.ULTRASOUND_FAST,
                volume=self.volume
            )

            if waveform:
                # Write to output stream
                self.output_stream.write(waveform)
                self.stats['packets_sent'] += 1
                logger.debug(f"GGWave sent packet: {packet.packet_id[:8]}...")
                return True
            else:
                logger.error("Failed to encode packet for audio transmission")
                self.stats['send_errors'] += 1
                return False

        except Exception as e:
            logger.error(f"Error sending GGWave packet: {e}")
            self.stats['send_errors'] += 1
            return False


class GGWaveReceiver(BaseTransportReceiver):
    """Handles receiving SOS packets over audio using GGWave."""

    def __init__(self, message_queue: asyncio.Queue, node_id: str):
        super().__init__(message_queue, node_id)
        self.pyaudio_instance = None
        self.ggwave_instance = None
        self.input_stream = None
        self.sample_rate = GGWAVE_SAMPLE_RATE
        self.samples_per_frame = GGWAVE_SAMPLES_PER_FRAME
        # For thread-safe communication between callback and async code
        self.decoded_queue = queue.Queue()
        self.processing_task = None

    async def start(self):
        """Initialize and start the GGWave receiver."""
        if not AUDIO_AVAILABLE:
            logger.warning("GGWave receiver unavailable. Audio libraries not installed.")
            return False

        try:
            # Initialize PyAudio
            self.pyaudio_instance = pyaudio.PyAudio()

            # Initialize GGWave
            self.ggwave_instance = pyggwave.GGWave()

            # Set up audio input stream with callback
            self.input_stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.samples_per_frame,
                stream_callback=self._audio_input_callback
            )

            self.running = True

            # Start background task to process decoded messages
            self.processing_task = asyncio.create_task(self._process_decoded_messages())

            logger.info(f"GGWave receiver started for node {self.node_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start GGWave receiver: {e}")
            self.stats['receive_errors'] += 1
            return False

    async def stop(self):
        """Stop the GGWave receiver."""
        self.running = False

        # Cancel processing task
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

        # Close input stream
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except Exception as e:
                logger.error(f"Error closing GGWave input stream: {e}")

        # Free GGWave instance
        if self.ggwave_instance:
            try:
                self.ggwave_instance.free()
            except Exception as e:
                logger.error(f"Error freeing GGWave instance: {e}")

        # Terminate PyAudio
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")

        logger.info("GGWave receiver stopped")

    def _audio_input_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio input stream - runs in a separate thread."""
        if not self.running or not self.ggwave_instance:
            return (None, pyaudio.paComplete)

        try:
            # Convert input data to the correct format
            audio_data = np.frombuffer(in_data, dtype=np.float32)

            # Try to decode any messages
            decoded = self.ggwave_instance.decode(audio_data)

            if decoded and len(decoded) > 0:
                # Place decoded data in queue for async processing
                self.decoded_queue.put(decoded)

            return (None, pyaudio.paContinue)

        except Exception as e:
            logger.error(f"Error in GGWave audio callback: {e}")
            return (None, pyaudio.paContinue)

    async def _process_decoded_messages(self):
        """Process decoded messages from the queue."""
        logger.info("GGWave message processor started")

        while self.running:
            try:
                # Check if there's data in the queue
                while not self.decoded_queue.empty():
                    # Get decoded data from queue
                    decoded = self.decoded_queue.get_nowait()

                    try:
                        # Convert to string
                        if isinstance(decoded, bytes):
                            decoded_str = decoded.decode('utf-8')
                        else:
                            decoded_str = str(decoded)

                        # Parse as SOSPacket
                        packet = SOSPacket.from_json(decoded_str)

                        # Skip packets sent by ourselves
                        if packet.sender_id == self.node_id:
                            continue

                        # Add to message queue
                        await self.message_queue.put(packet)
                        self.stats['packets_received'] += 1
                        logger.info(f"GGWave received packet: {packet.packet_id[:8]}... from {packet.sender_id[:8]}...")

                    except json.JSONDecodeError:
                        logger.warning(f"GGWave received invalid JSON: {decoded_str[:50]}...")
                        self.stats['receive_errors'] += 1
                    except (ValueError, KeyError) as e:
                        logger.warning(f"GGWave received invalid packet format: {e}")
                        self.stats['receive_errors'] += 1
                    except Exception as e:
                        logger.error(f"Error processing GGWave data: {e}")
                        self.stats['receive_errors'] += 1

                # Sleep to avoid CPU hogging
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in GGWave message processor: {e}")
                await asyncio.sleep(1)

        logger.info("GGWave message processor stopped")


class GGWaveTransport(BaseTransportManager):
    """Combined GGWave transport with both sending and receiving capabilities."""

    def __init__(self, message_queue: asyncio.Queue, node_id: str):
        # Create sender and receiver components
        sender = GGWaveSender(node_id)
        receiver = GGWaveReceiver(message_queue, node_id)

        # Initialize transport manager with components
        super().__init__(sender, receiver)

    async def start(self):
        """Start both GGWave sender and receiver components."""
        if not AUDIO_AVAILABLE:
            logger.warning("GGWave transport unavailable. Audio libraries not installed.")
            return False

        await super().start()
        logger.info("GGWave transport started (sender and receiver)")
        return True

    async def stop(self):
        """Stop both GGWave sender and receiver components."""
        await super().stop()
        logger.info("GGWave transport stopped (sender and receiver)")
