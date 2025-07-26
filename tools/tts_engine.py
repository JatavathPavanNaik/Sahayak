# tools/tts_engine.py

from google.cloud import texttospeech
import os

class GoogleTTS:
    def __init__(self, language_code="en-IN", voice_name="en-IN-Wavenet-D", speaking_rate=1.0):
        self.client = texttospeech.TextToSpeechClient()
        self.language_code = language_code
        self.voice_name = voice_name
        self.speaking_rate = speaking_rate

    def synthesize_speech(self, text, output_path="output.mp3"):
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=self.language_code,
            name=self.voice_name
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=self.speaking_rate
        )

        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        with open(output_path, "wb") as out:
            out.write(response.audio_content)
            print(f"Audio content written to {output_path}")
        return output_path
