#!/usr/bin/env python3
"""
GGWave receiver using pyggwave library
Modified to work with the pyggwave library used in the SonicNet project
"""

import pyaudio
import pyggwave
import numpy as np

def main():
    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # Audio configuration (matching the transport settings)
    sample_rate = 48000
    frames_per_buffer = 1024

    # Setup audio input stream
    stream = p.open(
        format=pyaudio.paFloat32,
        channels=1,
        rate=sample_rate,
        input=True,
        frames_per_buffer=frames_per_buffer
    )

    print('Listening for GGWave audio transmissions... Press Ctrl+C to stop')

    # Initialize GGWave instance using pyggwave API
    ggwave_instance = pyggwave.GGWave()

    try:
        while True:
            # Read audio data from microphone
            data = stream.read(frames_per_buffer, exception_on_overflow=False)

            # Convert bytes to numpy array for pyggwave
            audio_data = np.frombuffer(data, dtype=np.float32)

            # Try to decode using pyggwave
            try:
                decoded_text = ggwave_instance.decode(audio_data)

                if decoded_text:
                    print(f'Received text: {decoded_text}')

            except Exception as decode_error:
                # Silently continue - decode errors are common during normal operation
                pass

    except KeyboardInterrupt:
        print("\nStopping receiver...")

    finally:
        # Cleanup
        ggwave_instance.free()
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("Receiver stopped.")

if __name__ == "__main__":
    main()
