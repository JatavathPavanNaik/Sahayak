import queue
import threading
import time
from google.oauth2 import service_account
from google.cloud import speech_v1 as speech
from google.cloud import translate
import pyaudio
import os
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file


# Add these lines at the top (right after imports)
key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')  # Replace with your actual filename
print(f"Using credentials from: {key_path}")
credentials = service_account.Credentials.from_service_account_file(key_path)

# Configuration
RATE = 16000  # Sample rate (Hz)
CHUNK = 1024  # Audio chunk size (frames)
LANGUAGES = ["en-US", "es-ES", "fr-FR", "de-DE", "hi-IN", "ja-JP", "zh"]  # Supported languages
PROJECT_ID = os.getenv('GCP_PROJECT_ID') # Replace with your GCP Project ID

# Initialize clients
speech_client = speech.SpeechClient(credentials=credentials)
translate_client = translate.TranslationServiceClient(credentials=credentials)

class MicrophoneStream:
    """Opens a recording stream as a generator yielding audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]
            
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break
            yield b''.join(data)

def translate_text(text, target="en"):
    """Translates text to the target language."""
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    result = translate_client.translate_text(text, target_language=target)
    return result["translatedText"]

def listen_print_loop(responses):
    """Iterates through server responses and prints transcripts."""
    for response in responses:
        if not response.results:
            continue
            
        result = response.results[0]
        if not result.alternatives:
            continue
            
        transcript = result.alternatives[0].transcript
        detected_lang = result.language_code
        
        # Process final results only
        if result.is_final:
            print(f"\nDetected Language: {detected_lang}")
            print(f"Original Transcript: {transcript}")
            
            # Translate to English if not already English
            if not detected_lang.startswith("en"):
                translated = translate_text(transcript)
                print(f"Translation (en): {translated}")
            else:
                print(f"Transcript (en): {transcript}")
            print("\nListening...", end='', flush=True)

def main():
    # Configure speech recognition
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US",  # Default language
        alternative_language_codes=LANGUAGES,
        model="latest_long",
        enable_automatic_punctuation=True,
    )
    
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
        single_utterance=False
    )
    
    print("\n=== Speak now (Press Ctrl+C to stop) ===")
    print("Listening...", end='', flush=True)
    
    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )
        
        responses = speech_client.streaming_recognize(
            streaming_config,
            requests,
            timeout=300  # 5 minutes timeout
        )
        
        try:
            listen_print_loop(responses)
        except KeyboardInterrupt:
            print("\nStopped")

if __name__ == "__main__":
    main()