print(f"Importing modules...")

from transcriber_local import Transcriber
from scraper import DataSaver
from narrarate import narrate
from post_image_maker import make_reddit_post_image
from caption_maker import extract_word_timestamps_from_transcript


import json
import random
from sludge_video_extractor import Extractor
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
import os
import stat
import pathlib
import platform
import subprocess

from video_editing_functions import (
    scroll_image,
    stack_videos_vertically,
    add_fade_background,
    add_audio_to_video,
)


print(f"Successfully loaded all necessary support modules!")

SUBREDDIT_ICON_URL = "https://www.redditinc.com/assets/images/site/reddit-logo.png"
VIDEO_DIMS = (1080, 1920)
SLOP_VIDEO_VERTICAL_PERCENT = 0.4


SCROLLING_REDDIT_POST_HEIGHT = int(VIDEO_DIMS[1] * SLOP_VIDEO_VERTICAL_PERCENT)
SUB_SLUDGE_VIDEO_DIMS = (
    VIDEO_DIMS[0],
    int(VIDEO_DIMS[1] * SLOP_VIDEO_VERTICAL_PERCENT),
)


class PostUsageHistory:
    def __init__(self):
        self.fp = "post_usage_history.csv"

        if not os.path.exists(self.fp):
            with open(self.fp, "w") as f:
                f.write("example_post_url1,example_post_url2")

    def add_post(self, post_url):
        with open(self.fp, "a") as f:
            f.write(f",{post_url}")

    def get_all_posts(self):
        with open(self.fp, "r") as f:
            content = f.read().strip()
            if not content:
                return []
            return content.split(",")

    def post_exists(self, post_url):
        existing_posts = self.get_all_posts()
        if post_url in existing_posts:
            return True
        return False


def get_post_image(posts, expected_width):
    attempts = 0
    max_attempts = 5000
    while 1:
        attempts += 1

        if attempts > max_attempts:
            print(f"Failed to create a post image after {max_attempts} attempts.")
            break

        # select a random post
        random_post = random.choice(posts)
        post_data = random_post.to_dict()

        # if url has been used before, retry
        post_url = post_data["url"]
        post_usage_history = PostUsageHistory()
        if post_usage_history.post_exists(post_url):
            # print(f"Post {post_url} already used, skipping...")
            continue

        # try to use this stuff to make the post image
        image_path = make_reddit_post_image(
            thread=post_data["thread_name"],
            title_text=post_data["title"],
            body_text=post_data["content"],
            profile_img_url=post_data["profile_img"],
            subreddit_icon_url=SUBREDDIT_ICON_URL,
            username=post_data["username"],
            expected_width=expected_width,
            save=True,
        )

        # if making the image didnt work, retry with another post
        if image_path is None:
            # print(f"Failed to turn that into a post...")
            post_usage_history.add_post(post_url)
            continue

        # successfully made the image from an unused post
        post_usage_history.add_post(post_url)
        break


    return image_path, post_data


def cleanup_temp_files():
    folders = [
        r"temp",
        r"narrations",
        r"reddit_post_images",
    ]

    for folder_path in folders:
        folder = pathlib.Path(folder_path)

        if not folder.exists():
            continue

        for item in folder.rglob("*"):  # recursively find all contents
            try:
                if item.is_file():
                    make_deletable(item)
                    delete_file(item)
                elif item.is_dir():
                    # Only delete empty directories after files are gone
                    try:
                        item.rmdir()
                    except OSError:
                        # Directory not empty (yet), will retry later
                        pass
            except Exception as e:
                print(f"[!] Failed to delete {item}: {e}")

        # After clearing contents, attempt to remove any remaining empty subfolders
        for item in sorted(folder.rglob("*"), reverse=True):
            if item.is_dir():
                try:
                    item.rmdir()
                except Exception:
                    pass  # still not empty, or permission issue


def make_deletable(file):
    try:
        os.chmod(file, stat.S_IWUSR | stat.S_IRUSR)
    except Exception:
        pass


def delete_file(file):
    if platform.system() == "Windows":
        try:
            subprocess.run(
                ["takeown", "/f", str(file)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["icacls", str(file), "/grant", "Everyone:F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["del", "/f", "/q", str(file)],
                shell=True,
                check=False,
            )
        except Exception:
            pass
    else:
        try:
            file.unlink()
        except PermissionError:
            subprocess.run(["sudo", "rm", "-f", str(file)], check=False)


def create_stacked_reddit_scroll_video(output_dir):
    temp_folder_name = r"temp"
    os.makedirs(temp_folder_name, exist_ok=True)
    cleanup_temp_files()

    # get scraped post data
    print(f"[1] Getting saved scraped reddit data...")
    reddit_data_manager = DataSaver()
    posts = reddit_data_manager.get_all_posts()

    # create the static reddit post
    print(f"[2] Creating the static reddit post image...")
    post_image_save_path, post_data = get_post_image(
        posts, expected_width=VIDEO_DIMS[0]
    )
    if post_image_save_path in [False, None]:
        print(
            """[!] Fatal error: Could not create a reddit 
            post image in the given amount of tries."""
        )
        return False

    # make a narration of this post
    post_title = post_data["title"]
    post_text = post_data["content"]
    narration_content = f"{post_title}. {post_text}"

    narration_audio_file_path, narration_duration = narrate(
        "jf_alpha", narration_content
    )

    # make that a scrolling video
    print(f"[3] Converting the post image to a scrolling video...")
    scrolling_reddit_post_video_path = r"temp/reddit_post_scrolling_video.mp4"
    scroll_image(
        image_path=post_image_save_path,
        out_video_path=scrolling_reddit_post_video_path,
        scroll_duration=narration_duration,
        height=SCROLLING_REDDIT_POST_HEIGHT,
    )
   

    # craft the sub sludge video (subway
    # surfers, minecraft parkour, whatever)
    print(f"[4] Crafting a sub sludge video...")
    sub_sludge_extractor = Extractor()
    sub_sludge_video_path = r"temp/sub_sludge_video.mp4"
    sub_sludge_extractor.get_random_sludge_video(
        narration_duration, sub_sludge_video_path, SUB_SLUDGE_VIDEO_DIMS
    )
  

    # put the videos on top of eachother
    print(f"[5] Creating stacked video...")
    stacked_video_path = r"temp/stacked_video.mp4"
    stack_videos_vertically(
        scrolling_reddit_post_video_path, sub_sludge_video_path, stacked_video_path
    )

    # add fadebackground with pad
    print(f'[6] Adding the faded background...')
    stacked_video_with_background_path = r"temp/stacked_video_with_background.mp4"
    add_fade_background(
        stacked_video_path, sub_sludge_video_path, stacked_video_with_background_path
    )

    # narrate that stacked video
    print(f"[7] Adding narration to the stacked video...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    video_index = len(os.listdir(output_dir))
    narrated_video_path = f"{output_dir}/{video_index}.mp4"
    add_audio_to_video(
        video_path=stacked_video_with_background_path,
        audio_path=narration_audio_file_path,
        out_video_path=narrated_video_path,
    )
    
    
    print(f"Created a sludge video at {narrated_video_path}")
    cleanup_temp_files()
    return narrated_video_path, narration_content


def create_metadata(content):
    return {"placeholder": "content"}


def compile_video_and_metadata(video_path, metadata_dict, output_folder):
    if metadata_dict in [None, False]:
        print(f"Fatal error: This metadata is not valid: {metadata_dict}")
        return False

    this_output_index = len(os.listdir(output_folder))
    subfolder_name = f"video_{this_output_index}"
    subfolder_path = os.path.join(output_folder, subfolder_name)
    os.makedirs(subfolder_path, exist_ok=True)

    # move that vid to the subfolder
    new_video_path = os.path.join(subfolder_path, "video.mp4")
    os.rename(video_path, new_video_path)

    # metadata moving
    metadata_file_path = os.path.join(subfolder_path, "metadata.json")
    with open(metadata_file_path, "w") as f:
        json.dump(metadata_dict, f, indent=4)


from video_editing_functions import (
    caption_video,
)
from caption_maker import (
    generate_caption_frames,
)


def create_slop_with_captions_video():
    all_posts = DataSaver().get_all_posts()
    if len(all_posts) == 0:
        print(f"[!] Fatal error: DataSaver().get_all_posts() yielded no post objects!")
        return False

    # define criteria for post selection
    max_text_len = 2000
    min_text_len = 600

    # select a post that hasnt been used, and fits criteria
    post_history_module = PostUsageHistory()
    while 1:
        random_post = random.choice(all_posts)
        post_data = random_post.to_dict()

        # make sure post has valid text size
        text_len = len(post_data["content"])
        if text_len < min_text_len or text_len > max_text_len:
            all_posts.remove(random_post)
            continue

        # make sure post is new
        post_url = post_data["url"]
        if post_history_module.post_exists(post_url):
            all_posts.remove(random_post)
            continue

        # if we got here, we have a valid post
        post_history_module.add_post(post_url)
        break

    

    #narrate the post
    content_to_narrate = f"{post_data['title']}. {post_data['content']}"
    narration_file_path, narration_duration = narrate(
        "jf_alpha", content_to_narrate)
    
    #extract a slop video as background
    print(f"Extracting a slop video for the post...")
    slop_extractor = Extractor()
    slop_video_file_path = r"temp/slop_video.mp4"
    slop_extractor.get_random_sludge_video(
        narration_duration,
        slop_video_file_path,
        VIDEO_DIMS,
    )

    #transcribe the narration
    transcriber = Transcriber()
    transcript = transcriber.transcribe_to_srt(audio_path=narration_file_path)

    #generate captions for this video
    word_timestamps = extract_word_timestamps_from_transcript(transcript)
    frames = generate_caption_frames(
        word_timestamps, max_group_duration=2.5, max_words=5
    )
    captioned_video_path = "captioned_output.mp4"
    caption_video(slop_video_file_path, frames, out_video_path=captioned_video_path)
    
    #add narration
    narrated_captioned_video_path = "narrated_captioned_output.mp4"
    add_audio_to_video(
        captioned_video_path, narration_file_path, narrated_captioned_video_path
    )
    print(f'Created a narrated captioned video at {narrated_captioned_video_path}')


# main entry point functions
def create_all_stacked_reddit_scroll_videos(output_dir="final_vids"):
    while 1:
        try:
            narrated_video_path, narration_content = create_stacked_reddit_scroll_video(
                output_dir
            )
            metadata_dict = create_metadata(narration_content)
            compile_video_and_metadata(narrated_video_path, metadata_dict, output_dir)
        except:
            pass


if __name__ == "__main__":
    create_slop_with_captions_video()
