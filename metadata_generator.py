from transformers import pipeline
import re
import os
import json
import random


def sanitize_post_content(post_content: str) -> str:
    try:
        # Attempt to decode unicode escapes properly
        decoded = post_content.encode("utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        decoded = post_content  # fallback if decode fails

    # Remove any remaining smart quotes or unprintable characters
    decoded = re.sub(r"[^\x00-\x7F]+", "", decoded)  # strip non-ASCII
    return decoded.strip()


def benchmark():
    from transformers import pipeline
    import os, json, random

    reddit_data_folder = r"reddit_data"
    post_objects = os.listdir(reddit_data_folder)
    post_count = 5

    # --- Define models and prompts ---
    model_list = {
        "pegasus-xsum": "google/pegasus-xsum",
        "bart-cnn": "facebook/bart-large-cnn",
        "distilbart-cnn": "sshleifer/distilbart-cnn-12-6",
        "reddit-t5-small": "AventIQ-AI/Text-summarization-on-Reddit-posts-using-t5-small",
        "flan-t5-large": "google/flan-t5-large",
        "falcon-rw-1b": "tiiuae/falcon-rw-1b",
        "bge-small-en": "BAAI/bge-small-en",
        "bart-large-xsum": "facebook/bart-large-xsum",
        "t5-base": "t5-base",
        "c4ai-command-r-plus": "CohereForAI/c4ai-command-r-plus",
    }

    prompt_templates = {
        # Titles
        "title_direct": lambda text: text,
        "title_instruction": lambda text: f"Generate a short YouTube-worthy title for the following Reddit story:\n{text}",
        "title_summary_request": lambda text: f"Summarize this Reddit story in a catchy title for YouTube:\n{text}",
        "title_as_editor": lambda text: f"You are a YouTube editor. Craft a compelling title for this Reddit story:\n{text}",
        "title_clickbait": lambda text: f"Write a viral YouTube Short title based on this Reddit story. Make it emotional or surprising:\n{text}",
        "title_just_the_twist": lambda text: f"Write a short YouTube title that highlights the twist or unexpected moment in this story:\n{text}",
        "title_max_8_words": lambda text: f"Summarize this Reddit story into a YouTube Short title under 8 words:\n{text}",
        # Descriptions
        "description_instruction": lambda text: f"Write a 1-2 sentence engaging description for a YouTube Short based on this Reddit story:\n{text}",
        "description_as_narrator": lambda text: f"You are narrating this Reddit story for a YouTube Short. Write a brief description of what the viewer will hear:\n{text}",
        "description_with_hashtags": lambda text: f"Write a short description for a YouTube Short version of this Reddit story. Add 2-3 relevant hashtags:\n{text}",
        "description_why_watch": lambda text: f"Describe why this Reddit story is worth watching as a YouTube Short:\n{text}",
        "description_trailer_style": lambda text: f"Write a short, trailer-style description teasing the drama or punchline in this Reddit story:\n{text}",
        "description_ask_question": lambda text: f"Write a YouTube Short description that ends with a question to intrigue the viewer. Base it on this Reddit story:\n{text}",
        "description_as_uploader": lambda text: f"You just uploaded a YouTube Short based on this Reddit story. What would you write in the description field?\n{text}",
    }

    # --- Storage for all benchmark results ---
    all_benchmark_results = []

    for i in range(post_count):
        # --- Load random post ---
        random_post = random.choice(post_objects)
        post_path = os.path.join(reddit_data_folder, random_post)
        with open(post_path, "r", encoding="utf-8") as f:
            post_data = json.load(f)

        post_content_raw = post_data.get("content", "")
        post_title = post_data.get("title", "")
        full_post = post_title + sanitize_post_content(post_content_raw)

        post_info = {
            "index": i + 1,
            "path": post_path,
            "length": len(full_post),
            "content": full_post,
            "models": [],
        }

        for model_name, model_id in model_list.items():
            try:
                summarizer = pipeline("summarization", model=model_id, truncation=True)
            except Exception as e:
                print(f"[!] Failed to load model {model_name}: {e}")
                continue
            
            model_result = {"model": model_name, "outputs": []}

            for prompt_name, formatter in prompt_templates.items():
                try:
                    formatted_input = formatter(full_post)
                    summary = summarizer(
                        formatted_input,
                        max_new_tokens=60,
                        min_length=10,
                        do_sample=False,
                    )[0]["summary_text"]

                    model_result["outputs"].append(
                        {
                            "prompt": prompt_name,
                            "input_excerpt": formatted_input[:80].replace("\n", " "),
                            "output": summary.strip(),
                        }
                    )

                except Exception as e:
                    model_result["outputs"].append(
                        {
                            "prompt": prompt_name,
                            "input_excerpt": formatter(full_post)[:80].replace(
                                "\n", " "
                            ),
                            "output": f"ERROR: {str(e)}",
                        }
                    )

            post_info["models"].append(model_result)

        all_benchmark_results.append(post_info)

    # --- Output phase ---
    print(
        "\n\n========================== BENCHMARK SUMMARY ==========================\n"
    )

    for post in all_benchmark_results:
        print(f"\n--- Benchmark #{post['index']} ---")
        print(f"File: {post['path']}")
        print(f"Content Length: {post['length']} characters\n")

        for model in post["models"]:
            print(f"▶ MODEL: {model['model']}")
            for result in model["outputs"]:
                print(f"  [{result['prompt']}]")
                print(f"    ↳ Input:  {result['input_excerpt']}")
                print(f"    ↳ Output: {result['output']}\n")


if __name__ == "__main__":
    benchmark()
