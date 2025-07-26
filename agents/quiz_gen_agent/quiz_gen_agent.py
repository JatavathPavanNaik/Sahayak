from tools.tts_engine import GoogleTTS

tts = GoogleTTS(language_code="hi-IN", voice_name="hi-IN-Wavenet-A", speaking_rate=0.95)
tts.synthesize_speech("पानी जीवन के लिए अनिवार्य है।", output_path="hindi_output.mp3")
