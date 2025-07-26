from narration.kokoro.pipeline import KPipeline
import soundfile as sf
import time
import os
import wave
import re


def test_voices():
    voices_folder = r"kokoro.js/voices"
    out_folder = r"voice_tests"
    os.makedirs(out_folder, exist_ok=True)
    voices = [name.split(".")[0] for name in os.listdir(voices_folder)]
    print(voices)

    for voice in voices:
        pipeline = KPipeline(lang_code="a")
        text = "Kokoro is running from source on Windows 123!"
        generator = pipeline(text, voice=voice)

        for i, (gs, ps, audio) in enumerate(generator):
            print(f"{i}: {gs} -> {ps}")
            sf.write(f"{out_folder}/output_{voice}_{i}.wav", audio, 24000)


def list_voices():
    voices_folder = r"kokoro.js/voices"
    voices = [name.split(".")[0] for name in os.listdir(voices_folder)]
    print("Available voices:")
    for voice in voices:
        print("  -", voice)


def concatenate_wav_files(input_files, output_file):
    with wave.open(output_file, "wb") as output_wav:
        params_set = False  # Track if we've set the output parameters

        for input_file in input_files:
            with wave.open(input_file, "rb") as input_wav:
                if not params_set:
                    output_wav.setparams(input_wav.getparams())
                    params_set = True  # Ensure this only happens once

                output_wav.writeframes(input_wav.readframes(input_wav.getnframes()))

def clear_narrations(file_paths):
    for f in file_paths:
        try:
            os.remove(f)
            print(f"Removed {f}")
        except Exception as e:
            print(f"Error removing {f}: {e}")

def get_wav_duration(file_path):
    with wave.open(file_path, 'rb') as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        duration = frames / float(rate)
    return int(duration)+1


def remove_emojis_from_text(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r'', text)

def narrate(voice, text):
    text = remove_emojis_from_text(text)

    output_folder = r"narrations"
    os.makedirs(output_folder, exist_ok=True)
    this_audio_save_index = len(os.listdir(output_folder))
    files_in_dir = os.listdir(output_folder)
    pipeline = KPipeline(lang_code="a")
    generator = pipeline(text, voice=voice)

    part_file_paths = []
    for i, (gs, ps, audio) in enumerate(generator):
        print(f"{i}: {gs} -> {ps}")
        file_name = f"{voice}_{len(files_in_dir) + 1}_{i+1}.wav"
        file_path = os.path.join(output_folder, file_name)
        sf.write(file_path, audio, 24000)
        part_file_paths.append(file_path)

    combined_audio_file_path = f"{output_folder}/{this_audio_save_index}_{voice}.wav"
    concatenate_wav_files(part_file_paths, combined_audio_file_path)
    clear_narrations(part_file_paths)
    duration = get_wav_duration(combined_audio_file_path)
    return combined_audio_file_path, duration


if __name__ == "__main__":
    text = "ng for a cute guy’s number😭. So, hi. I’m back once again"
    print("Narrating text:", text)
    narrate("jf_alpha", text)

  
