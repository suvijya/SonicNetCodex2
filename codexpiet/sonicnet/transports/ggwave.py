"""
Enhanced GGWave transport for sending data over audio using pyggwave.
"""

import asyncio
import logging
import json
import time
from typing import Optional, Dict, Any

from .base import BaseTransport
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

class GGWaveTransport(BaseTransport):
    """Enhanced GGWave transport using pyggwave for audio communication."""

    def __init__(self, message_queue: asyncio.Queue, packet_manager):
        super().__init__(message_queue, packet_manager)
        self.running = False
        self.listen_task = None

        if not AUDIO_AVAILABLE:
            logger.warning("Audio libraries not available")
            return
        
        # Audio components
        self.pyaudio_instance = pyaudio.PyAudio()
        self.ggwave_instance = None
        self.input_stream = None
        self.output_stream = None

        # Audio configuration
        self.sample_rate = GGWAVE_SAMPLE_RATE
        self.samples_per_frame = GGWAVE_SAMPLES_PER_FRAME
        self.volume = int(GGWAVE_VOLUME)  # pyggwave expects int, not float

        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'audio_errors': 0,
            'decode_errors': 0
        }

    async def start(self):
        """Start the GGWave audio transport."""
        if not AUDIO_AVAILABLE:
            logger.warning("GGWave transport unavailable. Audio libraries not installed.")
            return

        try:
            # Initialize GGWave instance using correct API
            self.ggwave_instance = pyggwave.GGWave()

            # Setup audio input stream for receiving
            self.input_stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.samples_per_frame,
                stream_callback=self._audio_input_callback
            )

            # Setup audio output stream for sending
            self.output_stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.samples_per_frame
            )

            self.running = True
            self.listen_task = asyncio.create_task(self._receive_loop())

            logger.info("GGWave transport started successfully")

        except Exception as e:
            logger.error(f"Failed to start GGWave transport: {e}")
            self.stats['audio_errors'] += 1

    async def stop(self):
        """Stop the GGWave transport."""
        if not AUDIO_AVAILABLE:
            return

        self.running = False

        # Cancel receive task
        if self.listen_task and not self.listen_task.done():
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass

        # Close audio streams
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()

        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()

        # Free GGWave instance
        if self.ggwave_instance:
            self.ggwave_instance.free()

        # Cleanup PyAudio
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()

        logger.info("GGWave transport stopped")

    async def send(self, packet: SOSPacket):
        """Send a packet via audio using GGWave."""
        if not self.running or not self.ggwave_instance or not self.output_stream:
            return

        try:
            # Prepare packet data
            packet_data = packet.to_json()

            # Compress packet data for audio transmission
            compressed_data = self._compress_packet_data(packet_data)

            # Generate audio waveform using pyggwave API with ultrasound fast protocol
            waveform = self.ggwave_instance.encode(
                compressed_data,
                protocol=pyggwave.Protocol.ULTRASOUND_FAST,  # Changed to ultrasound fast
                volume=self.volume
            )

            if waveform:
                # Write directly to output stream (waveform is already in bytes format)
                self.output_stream.write(waveform)

                self.stats['messages_sent'] += 1
                logger.debug(f"Sent audio packet: {packet.packet_id}")
            else:
                logger.error("Failed to encode packet for audio transmission")

        except Exception as e:
            logger.error(f"Error sending audio packet: {e}")
            self.stats['audio_errors'] += 1

    def _audio_input_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio input stream - FIXED for better reliability."""
        if not self.running or not self.ggwave_instance:
            return (None, pyaudio.paComplete)

        try:
            # Convert input data to the correct format for pyggwave
            import numpy as np
            audio_data = np.frombuffer(in_data, dtype=np.float32)

            # Try to decode any messages using pyggwave
            try:
                decoded = self.ggwave_instance.decode(audio_data)

                if decoded and len(decoded) > 0:
                    logger.debug(f"GGWave decoded audio data: {len(decoded)} bytes")

                    try:
                        # Convert bytes to string
                        decoded_str = decoded.decode('utf-8') if isinstance(decoded, bytes) else str(decoded)

                        # Try direct packet parsing first (in case compression is disabled)
                        try:
                            packet = SOSPacket.from_json(decoded_str)
                        except:
                            # If that fails, try decompression
                            decompressed_data = self._decompress_packet_data(decoded_str)
                            packet = SOSPacket.from_json(decompressed_data)

                        # Add to message queue safely without await
                        try:
                            self.message_queue.put_nowait(packet)
                            self.stats['messages_received'] += 1
                            logger.info(f"GGWave received packet: {packet.packet_id[:8]}... from {packet.sender_id[:8]}...")
                        except asyncio.QueueFull:
                            logger.warning("Message queue full, dropping audio packet")

                    except Exception as e:
                        logger.error(f"Error parsing audio packet: {e}")
                        logger.debug(f"Raw decoded data: {decoded_str[:100]}...")
                        self.stats['decode_errors'] += 1
                else:
                    # No data decoded - this is normal, happens most of the time
                    pass

            except Exception as decode_error:
                # Decode errors are common when no audio signal is present
                logger.debug(f"GGWave decode attempt failed (normal): {decode_error}")

        except Exception as e:
            logger.error(f"Audio input callback error: {e}")
            self.stats['audio_errors'] += 1

        return (in_data, pyaudio.paContinue)

    async def _receive_loop(self):
        """Main receive loop for processing audio."""
        while self.running:
            try:
                # The actual receiving is handled by the audio callback
                # This loop just keeps the task alive and handles cleanup
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in GGWave receive loop: {e}")
                await asyncio.sleep(1)

    def _compress_packet_data(self, data: str) -> str:
        """Compress packet data for efficient audio transmission."""
        try:
            # Parse JSON to extract essential fields only
            packet_dict = json.loads(data)

            # Create minimal packet for audio transmission
            minimal_packet = {
                'id': packet_dict['packet_id'][:8],  # Shortened ID
                'from': packet_dict['sender_id'][-4:],  # Last 4 chars of sender
                'msg': packet_dict['message'][:50],  # Truncate message
                'type': packet_dict['packet_type'][0],  # First letter of type
                'urgency': packet_dict['urgency'][0],  # First letter of urgency
                'hops': packet_dict.get('hop_count', 0),
                'time': int(packet_dict['timestamp'])
            }

            # Add location if available
            if 'gps_location' in packet_dict:
                gps = packet_dict['gps_location']
                minimal_packet['lat'] = round(gps['latitude'], 4)
                minimal_packet['lon'] = round(gps['longitude'], 4)

            return json.dumps(minimal_packet, separators=(',', ':'))

        except Exception as e:
            logger.error(f"Error compressing packet data: {e}")
            return data  # Return original if compression fails

    def _decompress_packet_data(self, compressed_data: str) -> str:
        """Decompress packet data received via audio."""
        try:
            minimal_packet = json.loads(compressed_data)

            # Reconstruct full packet structure
            full_packet = {
                'packet_id': minimal_packet['id'],
                'sender_id': f"audio_{minimal_packet['from']}",
                'message': minimal_packet['msg'],
                'packet_type': self._expand_type(minimal_packet['type']),
                'urgency': self._expand_urgency(minimal_packet['urgency']),
                'hop_count': minimal_packet.get('hops', 0),
                'timestamp': minimal_packet['time'],
                'location_text': 'Audio transmission',
                'relay_path': [f"audio_{minimal_packet['from']}"],
                'ttl': 10,
                'thread_id': minimal_packet['id'],
                'requires_ack': False,
                'ack_received': False,
                'ack_nodes': [],
                'received_via': ['audio'],
                'signal_strength': {},
                'battery_level': None,
                'media_attachments': []
            }

            # Add GPS location if available
            if 'lat' in minimal_packet and 'lon' in minimal_packet:
                full_packet['gps_location'] = {
                    'latitude': minimal_packet['lat'],
                    'longitude': minimal_packet['lon'],
                    'altitude': None,
                    'accuracy': None,
                    'timestamp': minimal_packet['time']
                }
                full_packet['location_text'] = f"{minimal_packet['lat']}, {minimal_packet['lon']}"

            return json.dumps(full_packet)

        except Exception as e:
            logger.error(f"Error decompressing packet data: {e}")
            return compressed_data  # Return as-is if decompression fails

    def _expand_type(self, short_type: str) -> str:
        """Expand abbreviated packet type."""
        type_map = {
            'S': 'SOS',
            'U': 'STATUS_UPDATE',
            'A': 'ALL_CLEAR',
            'H': 'HEARTBEAT',
            'K': 'ACK'
        }
        return type_map.get(short_type, 'SOS')

    def _expand_urgency(self, short_urgency: str) -> str:
        """Expand abbreviated urgency level."""
        urgency_map = {
            'C': 'CRITICAL',
            'H': 'HIGH',
            'M': 'MEDIUM',
            'L': 'LOW'
        }
        return urgency_map.get(short_urgency, 'HIGH')

    def get_transport_stats(self) -> Dict[str, Any]:
        """Get GGWave transport statistics."""
        return {
            **self.stats,
            'audio_available': AUDIO_AVAILABLE,
            'running': self.running,
            'sample_rate': self.sample_rate,
            'volume': self.volume
        }

    def test_audio_system(self) -> bool:
        """Test if audio system is working properly."""
        if not AUDIO_AVAILABLE:
            return False

        try:
            # Quick test of audio system
            test_instance = self.pyaudio_instance
            info = test_instance.get_default_input_device_info()
            logger.info(f"Audio input device: {info['name']}")
            return True
        except Exception as e:
            logger.error(f"Audio system test failed: {e}")
            return False
