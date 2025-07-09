from TTS.api import TTS
import os

# List available models
print(TTS.list_models())

# Load a model
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)

# Generate speech
audio_folder = 'narratations'
os.makedirs(audio_folder, exist_ok=True)
tts.tts_to_file(text="This is a test.", file_path=r"audio_folder/output.wav")
