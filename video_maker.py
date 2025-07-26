print(f"Importing modules...")

from metadata_generator import PostMetadataGenerator 
import json
from scraper import DataSaver
import cv2
from narrarate import narrate
import random
from post_image_maker import make_reddit_post_image
from sludge_video_extractor import Extractor
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
import os
import stat
import pathlib
import platform
import subprocess


print(f"Successfully loaded all necessary support modules!")

SUBREDDIT_ICON_URL = "https://www.redditinc.com/assets/images/site/reddit-logo.png"
VIDEO_DIMS = (1080, 1920)
SCROLLING_REDDIT_POST_HEIGHT = int(VIDEO_DIMS[1] / 2)
SUB_SLUDGE_VIDEO_DIMS = (VIDEO_DIMS[0], int(VIDEO_DIMS[1] / 2))


class PostUsageHistory:
    def __init__(self):
        self.fp = "post_usage_history.csv"

        if not os.path.exists(self.fp):
            with open(self.fp, "w") as f:
                f.write('example_post_url1,example_post_url2')

    def add_post(self, post_url):
        with open(self.fp, "a") as f:
            f.write(f",{post_url}")

    def get_all_posts(self):
        with open(self.fp, "r") as f:
            content = f.read().strip()
            if not content:
                return []
            return content.split(",")
        
    def post_exists(self,post_url):
        existing_posts = self.get_all_posts()
        if post_url in existing_posts:
            return True
        return False

def get_video_duration(video_path):
    video = VideoFileClip(video_path)
    duration = video.duration
    video.close()
    return duration


def resize_video(video_path, output_path, width, height):
    print(f"Resizing video: {video_path} to {width}x{height}...")

    # Load the video
    video = VideoFileClip(video_path)

    # Resize video
    resized_video = video.resize(newsize=(width, height))

    # Write the result
    resized_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

    print(f"Resized video saved to {output_path}")
    return output_path


def make_blur_video(video_path, output_path, blur_amount):
    print(
        f"Creating a blurred video from {video_path} with blur amount {blur_amount}..."
    )

    # Ensure blur_amount is odd and >= 1 (required by cv2.GaussianBlur)
    if blur_amount % 2 == 0:
        blur_amount += 1
    if blur_amount < 1:
        blur_amount = 1

    # Define a frame-blurring function using OpenCV
    def blur_frame(frame):
        return cv2.GaussianBlur(frame, (blur_amount, blur_amount), 0)

    # Load the video and apply blur
    video = VideoFileClip(video_path)
    blurred_video = video.fl_image(blur_frame)

    # Write the result

    blurred_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

    print(f"Blurred video saved to {output_path}")
    return output_path


def get_video_dims(video_path):

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    return width, height


def resize_video_keep_aspect_ratio(video_path, output_path, target_width):
    print(f"Resizing video: {video_path} to width {target_width}...")

    # Load the video
    video = VideoFileClip(video_path)

    # Calculate new height to preserve aspect ratio
    aspect_ratio = video.h / video.w
    target_height = int(target_width * aspect_ratio)

    # Resize video
    resized_video = video.resize(newsize=(target_width, target_height))

    # Write the result
    resized_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

    print(f"Resized video saved to {output_path}")
    return output_path


def paste_video_onto_video(
    foreground_video, background_video, foreground_video_pad, output_path
):
    # Step 1: Get original foreground width
    foreground_width, _ = get_video_dims(foreground_video)
    new_foreground_width = foreground_width - (foreground_video_pad * 2)

    # Step 2: Resize foreground while keeping aspect ratio
    foreground_video_resized = resize_video_keep_aspect_ratio(
        foreground_video, r"temp/foreground_resized.mp4", new_foreground_width
    )

    # Step 3: Load background and foreground clips
    background_clip = VideoFileClip(background_video)
    foreground_clip = VideoFileClip(foreground_video_resized)

    # Step 4: Center foreground on background
    x_center = (background_clip.w - foreground_clip.w) // 2
    y_center = (background_clip.h - foreground_clip.h) // 2
    foreground_clip = foreground_clip.set_position((x_center, y_center))

    # Step 5: Match background duration to foreground
    background_clip = background_clip.set_duration(foreground_clip.duration)

    # Step 6: Composite the two clips
    final = CompositeVideoClip([background_clip, foreground_clip])
    final = final.set_audio(foreground_clip.audio)  # foreground audio dominates

    # Step 7: Write to file
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")

    print(f"Pasted video saved to {output_path}")
    return output_path


def add_fade_background(main_video, fade_video, output_path):
    main_video_duration = get_video_duration(main_video)
    fade_video_duration = get_video_duration(fade_video)

    print(f"Dims of main video are {get_video_dims(main_video)}")
    print(f"Dims of fade video are {get_video_dims(fade_video)}")

    if main_video_duration != fade_video_duration:
        print("[!] Fatal error: Main video and fade video durations do not match!")
        return False

    # resize the background video to same dims are foreground video
    full_background_dims = get_video_dims(main_video)
    resized_backgrond_video_path = r"temp/resized_fade_video.mp4"
    resize_video(
        fade_video,
        resized_backgrond_video_path,
        full_background_dims[0],
        full_background_dims[1],
    )
    print(f"Reszied background video to {get_video_dims(resized_backgrond_video_path)}")

    # fade that video
    fade_video_background_clip_path = r"temp/fade_video_background_70.mp4"
    make_blur_video(resized_backgrond_video_path, fade_video_background_clip_path, 70)
    print(
        f"Dims of blurred background video are {get_video_dims(fade_video_background_clip_path)}"
    )

    print(f"pasting videos together...")
    print(f"\tmain video dims: {get_video_dims(main_video)}")
    print(f"\tfade video dims: {get_video_dims(fade_video_background_clip_path)}")

    paste_video_onto_video(main_video, fade_video_background_clip_path, 50, output_path)
    print("Dims of resultant video are", get_video_dims(output_path))


def scroll_image(image_path, out_video_path, scroll_duration, height):
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Image not found or unable to read.")

    # Get image dimensions
    img_height, img_width, _ = image.shape

    # Calculate the number of frames needed for the scroll
    fps = 30  # Frames per second
    total_frames = int(scroll_duration * fps)

    # Create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    print(
        f"Calling cv2.videowriting with these params: \n out_video_path: {out_video_path}, fourcc: {fourcc}, fps: {fps}, dims: ({img_width}, {height})"
    )
    out = cv2.VideoWriter(out_video_path, fourcc, fps, (img_width, height))

    for i in range(total_frames):
        # Calculate the vertical offset for scrolling
        offset = int((i / total_frames) * (img_height - height))
        frame = image[offset : offset + height, :, :]
        out.write(frame)

    out.release()
    print(f"Video saved to {out_video_path}")


def get_post_image(posts, expected_width):
    attempts = 0
    max_attempts = 5000
    while 1:
        attempts += 1

        if attempts > max_attempts:
            print(f"Failed to create a post image after {max_attempts} attempts.")
            break

        #select a random post
        random_post = random.choice(posts)
        post_data = random_post.to_dict()
        
        #if url has been used before, retry
        post_url = post_data["url"]
        post_usage_history = PostUsageHistory()
        if post_usage_history.post_exists(post_url):
            print(f"Post {post_url} already used, skipping...")
            continue

        #try to use this stuff to make the post image
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

        #if making the image didnt work, retry with another post
        if image_path is None:
            print(f"Failed to turn that into a post...")
            continue

        #successfully made the image from an unused post
        post_usage_history.add_post(post_url)
        break

    print(f"Post image created successfully after {attempts} attempts.")

    return image_path, post_data


def stack_videos_vertically(top_video_path, bottom_video_path, out_video_path):
    cap1 = cv2.VideoCapture(top_video_path)
    cap2 = cv2.VideoCapture(bottom_video_path)

    # Ensure both videos are open
    if not cap1.isOpened():
        raise ValueError(
            f"top_video_path: {top_video_path} is invalid or cannot be opened."
        )
    if not cap2.isOpened():
        raise ValueError(
            f"bottom_video_path: {bottom_video_path} is invalid or cannot be opened."
        )

    # Get properties (assume same fps)
    fps = cap1.get(cv2.CAP_PROP_FPS)
    width1 = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
    height1 = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))

    width2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
    height2 = int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Resize to same width (if needed)
    common_width = min(width1, width2)

    height1_resized = int(height1 * common_width / width1)
    height2_resized = int(height2 * common_width / width2)
    out_height = height1_resized + height2_resized

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(out_video_path, fourcc, fps, (common_width, out_height))

    while True:
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()

        if not ret1 or not ret2:
            break

        frame1_resized = cv2.resize(frame1, (common_width, height1_resized))
        frame2_resized = cv2.resize(frame2, (common_width, height2_resized))

        stacked = cv2.vconcat([frame1_resized, frame2_resized])
        out.write(stacked)

    cap1.release()
    cap2.release()
    out.release()
    print(f"Saved stacked video to: {out_video_path}")


def add_audio_to_video(video_path, audio_path, out_video_path):
    print(f"Adding audio from {audio_path} to video {video_path}...")

    # Load the video and audio
    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)

    # Match the audio duration to the video duration (trim if needed)
    if audio.duration > video.duration:
        audio = audio.subclip(0, video.duration)

    # Set the audio to the video
    final_video = video.set_audio(audio)

    # Write the final video
    final_video.write_videofile(out_video_path, codec="libx264", audio_codec="aac")

    print(f"Saved final video with audio to {out_video_path}")
    return out_video_path


def cleanup_files():
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


def create_sludge_video(output_dir):
    temp_folder_name = r"temp"
    os.makedirs(temp_folder_name, exist_ok=True)
    cleanup_files()


    # get scraped post data
    print(f"Getting saved scraped reddit data...")
    reddit_data_manager = DataSaver()
    posts = reddit_data_manager.get_all_posts()

    # create the static reddit post
    print(f"Creating the static reddit post image...")
    post_image_save_path, post_data = get_post_image(
        posts, expected_width=VIDEO_DIMS[0]
    )
    if post_image_save_path in [False, None]:
        print(
            """[!] Fatal error: Could not create a reddit 
            post image in the given amount of tries."""
        )
        return False
    print(
        f"""Post image was created successfully here: 
        {post_image_save_path}."""
    )

    # make a narration of this post
    post_title = post_data["title"]
    post_text = post_data["content"]
    narration_content = f"{post_title}. {post_text}"

    narration_audio_file_path, narration_duration = narrate(
        "jf_alpha", narration_content
    )

    # make that a scrolling video
    print(f"Converting the post image to a scrolling video...")
    scrolling_reddit_post_video_path = r"temp/reddit_post_scrolling_video.mp4"
    print(f"Scrolling the post image for {narration_duration} seconds...")
    print(
        f"Creating scroll image with these params: \n image_path: {post_image_save_path}, out_video_path: {scrolling_reddit_post_video_path}, scroll_duration: {narration_duration}, height: {SCROLLING_REDDIT_POST_HEIGHT}"
    )
    print(f"About to create scrolling video...")
    scroll_image(
        image_path=post_image_save_path,
        out_video_path=scrolling_reddit_post_video_path,
        scroll_duration=narration_duration,
        height=SCROLLING_REDDIT_POST_HEIGHT,
    )
    print(
        f"Just created a scrolling video of the post image here: {scrolling_reddit_post_video_path}. Press Enter to continue..."
    )

    # craft the sub sludge video (subway
    # surfers, minecraft parkour, whatever)
    print(f"Crafting a sub sludge video...")
    sub_sludge_extractor = Extractor()
    sub_sludge_video_path = r"temp/sub_sludge_video.mp4"
    sub_sludge_extractor.get_random_sludge_video(
        narration_duration, sub_sludge_video_path, SUB_SLUDGE_VIDEO_DIMS
    )
    print(
        f"Created a sub sludge video here: {sub_sludge_video_path}. Press Enter to continue..."
    )

    # put the videos on top of eachother
    print(f"Creating stacked video...")
    stacked_video_path = r"temp/stacked_video.mp4"
    stack_videos_vertically(
        scrolling_reddit_post_video_path, sub_sludge_video_path, stacked_video_path
    )
    print(f"Created stacked video at {stacked_video_path}")

    # add fadebackground with pad
    stacked_video_with_background_path = r"temp/stacked_video_with_background.mp4"
    add_fade_background(
        stacked_video_path, sub_sludge_video_path, stacked_video_with_background_path
    )

    # narrate that stacked video
    print(f"Adding narration to the stacked video...")
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

    cleanup_files()

    return narrated_video_path, narration_content


def create_metadata(content):
    metadata_generator = PostMetadataGenerator()
    metadata = metadata_generator.generate_youtube_metadata(content)
    return metadata

def compile_video_and_metadata(video_path, metadata_dict, output_folder):
    if metadata_dict in [None, False]:
        print(f'Fatal error: This metadata is not valid: {metadata_dict}')
        return False
    
    this_output_index = len(os.listdir(output_folder))
    subfolder_name = f"video_{this_output_index}"
    subfolder_path = os.path.join(output_folder, subfolder_name)
    os.makedirs(subfolder_path, exist_ok=True)

    #move that vid to the subfolder
    new_video_path = os.path.join(subfolder_path, "video.mp4")
    os.rename(video_path, new_video_path)

    #metadata moving
    metadata_file_path = os.path.join(subfolder_path, "metadata.json")
    with open(metadata_file_path, "w") as f:
        json.dump(metadata_dict, f, indent=4)
    print(f"Saved metadata to {metadata_file_path}")


def create_all_sludge_videos(output_dir="final_vids"):
    while 1:
        try:
            narrated_video_path, narration_content = create_sludge_video(output_dir)
            metadata_dict = create_metadata(narration_content)
            compile_video_and_metadata(narrated_video_path, metadata_dict, output_dir)
        except:
            pass


if __name__ == "__main__":
    create_all_sludge_videos(output_dir="final_vids")

   
