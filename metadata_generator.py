from transformers import pipeline
import os, json, random, re, csv, time
from typing import List, Dict


def sanitize_post_content(post_content: str) -> str:
    try:
        # Attempt to decode unicode escapes properly
        decoded = post_content.encode("utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        decoded = post_content  # fallback if decode fails

    # Remove any remaining smart quotes or unprintable characters
    decoded = re.sub(r"[^\x00-\x7F]+", "", decoded)  # strip non-ASCII
    return decoded.strip()


import csv
import os


class BenchmarkDataSaver:
    def __init__(self, csv_path="benchmark_data.csv"):
        self.csv_path = csv_path
        self.headers = [
            "generation_time_taken",
            "generation_type",  # either 'title' or 'description'
            "model_name",
            "base_prompt",
            "generated_text",
            "post_text",
        ]
        # Create CSV file with headers if it doesn't exist
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writeheader()

    def add_to_csv(self, data: dict):
        """
        Appends a new row to the CSV.
        `data` must be a dict with keys matching self.headers
        """
        if not all(key in data for key in self.headers):
            raise ValueError(f"Data must include all fields: {self.headers}")
        with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writerow(data)

    def row_exists(
        self, generation_type: str, base_prompt: str, post_text: str, model_name: str
    ) -> bool:
        """
        Checks if a row with the given generation_type, base_prompt, and post_text exists.
        """
        with open(self.csv_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (
                    row["generation_type"] == generation_type
                    and row["base_prompt"] == base_prompt
                    and row["post_text"] == post_text
                    and row["model_name"] == model_name
                ):
                    return True
        return False


def get_random_post(reddit_data_folder):
    cut_amount = 100
    post_objects = os.listdir(reddit_data_folder)[:cut_amount]
    random_post = random.choice(post_objects)
    post_path = os.path.join(reddit_data_folder, random_post)
    with open(post_path, "r", encoding="utf-8") as f:
        post_data = json.load(f)

    post_content_raw = post_data.get("content", "")
    post_title = post_data.get("title", "")
    full_post = post_title + sanitize_post_content(post_content_raw)

    return {
        "path": post_path,
        "raw_content": post_content_raw,
        "title": post_title,
        "content": full_post,
    }


def benchmark(
    model_list: Dict[str, str],
    prompt_word_limits: dict = {"title": 10, "description": 50},
    post_count=500,
    post_data_folder=r"reddit_data",
):
    results_saver = BenchmarkDataSaver()

    # Select and shuffle posts
    post_infos = [get_random_post(post_data_folder) for _ in range(post_count)]
    random.shuffle(post_infos)

    for post_info in post_infos:
        input_text = post_info["content"]

        for model_name, model_id in model_list.items():
            base_prompt = "None"


            try:
                summarizer = pipeline("summarization", model=model_id, truncation=True)
            except:
                print("Incompatible model:", model_name)

            if results_saver.row_exists("title", base_prompt, input_text, model_name):
                print(f"SKIP title | model={model_name} | prompt={base_prompt}")
                continue


            # Start timing
            start_time = time.time()

            summary_text = summarizer(
                input_text,
                max_new_tokens=prompt_word_limits["title"] * 2,
                min_length=5,
                do_sample=False,
            )[0]["summary_text"]

            elapsed_time = round(time.time() - start_time, 3)

            results_saver.add_to_csv(
                {
                    "generation_time_taken": elapsed_time,
                    "generation_type": "title",
                    "base_prompt": base_prompt,
                    "generated_text": summary_text,
                    "post_text": input_text,
                    "model_name": model_name,
                }
            )
            print(f"✔ SAVED title | model={model_name} | prompt={base_prompt}")

            if results_saver.row_exists(
                "description", base_prompt, input_text, model_name
            ):
                print(f"SKIP desc  | model={model_name} | prompt={base_prompt}")
                continue


            # Start timing
            start_time = time.time()

            summary_text = summarizer(
                input_text,
                max_new_tokens=prompt_word_limits["description"] * 2,
                min_length=10,
                do_sample=False,
            )[0]["summary_text"]

            elapsed_time = round(time.time() - start_time, 3)

            results_saver.add_to_csv(
                {
                    "generation_time_taken": elapsed_time,
                    "generation_type": "description",
                    "base_prompt": base_prompt,
                    "generated_text": summary_text,
                    "post_text": input_text,
                    "model_name": model_name,
                }
            )
            print(f"✔ SAVED desc  | model={model_name} | prompt={base_prompt}")


if __name__ == "__main__":
    model_list = {
        "long-t5": "google/long-t5-tglobal-base",
        "bigbird-pegasus": "google/bigbird-pegasus-large-arxiv",
        "led-base": "allenai/led-base-16384",
        "mbart-multilingual": "facebook/mbart-large-50-many-to-many-mmt",
        "mt5-small": "google/mt5-small",
        "prophetnet-large": "microsoft/prophetnet-large-uncased",
        "pegasus-xsum": "google/pegasus-xsum",
        "bart-cnn": "facebook/bart-large-cnn",
        "distilbart-cnn": "sshleifer/distilbart-cnn-12-6",
        "reddit-t5-small": "AventIQ-AI/Text-summarization-on-Reddit-posts-using-t5-small",
        "flan-t5-large": "google/flan-t5-large",
        "bge-small-en": "BAAI/bge-small-en",
        "bart-large-xsum": "facebook/bart-large-xsum",
        "t5-base": "t5-base",
        "c4ai-command-r-plus": "CohereForAI/c4ai-command-r-plus",
    }

    title_prompt_templates = {
        f"Generate a short YouTube-worthy title for the following Reddit story:",
        f"Summarize this Reddit story in a catchy title for YouTube:",
        f"You are a YouTube editor. Craft a compelling title for this Reddit story:",
        f"Write a viral YouTube Short title based on this Reddit story. Make it emotional or surprising:",
        f"Write a short YouTube title that highlights the twist or unexpected moment in this story:",
        f"Summarize this Reddit story into a YouTube Short title under 8 words:",
    }

    description_prompt_templates = {
        f"Write a 1-2 sentence engaging description for a YouTube Short based on this Reddit story:",
        f"You are narrating this Reddit story for a YouTube Short. Write a brief description of what the viewer will hear:",
        f"Write a short description for a YouTube Short version of this Reddit story. Add 2-3 relevant hashtags:",
        f"Describe why this Reddit story is worth watching as a YouTube Short:",
        f"Write a short, trailer-style description teasing the drama or punchline in this Reddit story:",
        f"Write a YouTube Short description that ends with a question to intrigue the viewer. Base it on this Reddit story:",
        f"You just uploaded a YouTube Short based on this Reddit story. What would you write in the description field?",
    }

    benchmark(model_list)
