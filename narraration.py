import random
from TTS.api import TTS
from TTS.utils.manage import ModelManager
import os
import time
import re

from scraper import DataSaver

ds = DataSaver()

os.environ["COQUI_TOS_AGREED"] = "1"


def get_random_reddit_post(max_len=900):
    """Keep trying until a post shorter than max_len is found."""
    posts = ds.get_all_posts()
    while True:
        post = random.choice(posts).to_dict()['content']
        if len(post) <= max_len:
            return post

def is_espeak_error(exception):
    """Check if the error is related to missing espeak."""
    return (
        "espeak" in str(exception).lower() and
        "no espeak backend found" in str(exception).lower()
    ) or "Failed to load espeak-data" in str(exception)

def test_narration_models(output_folder):
    narration_text = get_random_reddit_post()

    # Output folder
    os.makedirs(output_folder, exist_ok=True)

    # Show preview of narration text
    print("\n📝 Selected Reddit Post for Narration:")
    print("-" * 50)
    print(narration_text)
    print("-" * 50 + "\n")

    # Function to sanitize filenames
    def safe_filename(model_name):
        return re.sub(r'[^\w\-_.]', '_', model_name)

    # Track total time
    start_total = time.time()

    # Get all available models
    model_manager = ModelManager()
    all_models = model_manager.list_models()

    for index, model_name in enumerate(all_models, 1):
        print(f"\n🎤 [{index}/{len(all_models)}] Processing model: {model_name}")
        model_start = time.time()

        try:
            tts = TTS(model_name=model_name, progress_bar=False, gpu=False)
            model_filename = safe_filename(model_name) + ".wav"
            output_path = os.path.join(output_folder, model_filename)

            print(f" > Synthesizing audio...")
            tts.tts_to_file(text=narration_text, file_path=output_path)

            # Also save the text as a .txt file for reference
            with open(output_path.replace(".wav", ".txt"), 'w', encoding='utf-8') as f:
                f.write(narration_text)

            print(f" > Saved to: {output_path}")
            print(f" > Time taken: {time.time() - model_start:.2f} sec")

        except Exception as e:
            if is_espeak_error(e):
                print(f" ⚠️ Skipped model {model_name} — requires `espeak`, which is not installed or configured.")
            else:
                print(f" ❌ Failed on model {model_name}: {e}")

    print(f"\n✅ All models processed. Total time: {time.time() - start_total:.2f} seconds.")

if __name__ == '__main__':
    test_narration_models('narration_test')
