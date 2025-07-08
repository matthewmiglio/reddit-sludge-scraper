from PIL import Image, ImageDraw, ImageFont
from IPython.display import display
import requests
from io import BytesIO
import matplotlib.pyplot as plt
import random

# --- Constants ---
IMG_WIDTH, IMG_HEIGHT = 360, 640
MARGIN = 16
LINE_SPACING = 6

# Fonts
FONT_TITLE = r"reddit_assets/fonts/Noto_Sans/static/NotoSans-Bold.ttf"
FONT_BODY = r"reddit_assets/fonts/Noto_Sans/static/NotoSans-Regular.ttf"
FONT_SEARCH = r"reddit_assets\fonts\Noto_Sans\static\NotoSans-SemiBold.ttf"
font_title = ImageFont.truetype(FONT_TITLE, size=18)
font_body = ImageFont.truetype(FONT_BODY, size=14)
font_search = ImageFont.truetype(FONT_SEARCH, size=12)


def make_reddit_post_image(thread, title_text, body_text, profile_img_url, subreddit_icon_url, username):
    if len(body_text)>900:
        print('[!] Error: your body text is too long itll be cut off')
        return None
    if len(thread) > 17:
        print('[!] Error: your thread name is too long itll be cut off')
        return None
    if len(username) > 27:
        print('[!] Error: your username is too long itll be cut off')
        return None

    post_age= f'{random.randint(1,19)}h'
    base_image_path = "reddit_assets/images/base_post_image.png"
    img = Image.open(base_image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Draw subreddit name in search bar
    draw.text((170, 18), thread, font=font_search, fill="#333333")

    # Draw subreddit icon
    try:
        response = requests.get(subreddit_icon_url)
        subreddit_icon = Image.open(BytesIO(response.content)).convert("RGBA").resize((20, 20))
        mask_icon = Image.new("L", (20, 20), 0)
        ImageDraw.Draw(mask_icon).ellipse((0, 0, 20, 20), fill=255)
        img.paste(subreddit_icon, (85, 25), mask_icon)
    except Exception as e:
        print("[!] Error: Failed to load subreddit icon:", e)

    # Draw profile avatar
    try:
        response = requests.get(profile_img_url)
        avatar = Image.open(BytesIO(response.content)).convert("RGBA").resize((32, 32))
        mask = Image.new("L", (32, 32), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 32, 32), fill=255)
        img.paste(avatar, (MARGIN, 60), mask)
    except Exception as e:
        print("[!] Error: Failed to load profile image:", e)

    # Draw username and timestamp
    draw.text((MARGIN + 40, 60), f"{username} · {post_age} ago", font=font_body, fill="gray")

    # Text wrapping function
    def draw_wrapped_text(draw, text, font, x, y, max_width):
        paragraphs = text.split('\n')  # handles \n and \n\n naturally
        for para in paragraphs:
            if para.strip() == "":
                # Add paragraph spacing
                y += font.getbbox("A")[3] - font.getbbox("A")[1] + LINE_SPACING
                continue

            words = para.split()
            line = ""
            for word in words:
                test_line = f"{line} {word}".strip()
                bbox = font.getbbox(test_line)
                line_width = bbox[2] - bbox[0]
                if line_width <= max_width:
                    line = test_line
                else:
                    draw.text((x, y), line, font=font, fill="black")
                    y += font.getbbox(line)[3] - font.getbbox(line)[1] + LINE_SPACING
                    line = word
            if line:
                draw.text((x, y), line, font=font, fill="black")
                y += font.getbbox(line)[3] - font.getbbox(line)[1] + LINE_SPACING
        return y

    # Draw title and body
    content_y_start = 60 + 32 + 10
    y = draw_wrapped_text(draw, title_text, font_title, MARGIN, content_y_start, IMG_WIDTH - 2 * MARGIN)
    y += 8
    y = draw_wrapped_text(draw, body_text, font_body, MARGIN, y, IMG_WIDTH - 2 * MARGIN)

    return img


import os

class ImageSaver:
    def __init__(self, save_path='reddit_post_images'):
        self.save_path = save_path
        if not os.path.exists(save_path):
            os.makedirs(save_path)

    def save_image(self, img, thread_name, ):
        uuid = str(random.randint(10000,99999))[:8]  # Generate a short unique identifier
        file_name = f'{uuid}.png'
        subfolder = thread_name.replace(' ', '_').replace('/', '_')
        subfolder_path = os.path.join(self.save_path, subfolder)
        if not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)
        image_path = os.path.join(self.save_path, subfolder,file_name)

        img.save(image_path)
        print(f"Image saved as {image_path}")

    def get_all_images(self):
        import os
        return [f for f in os.listdir(self.save_path) if f.endswith('.png')]

from scraper import DataSaver



if __name__ == '__main__':
    ds = DataSaver()
    image_saver = ImageSaver()
    posts = ds.get_all_posts()
    for post in posts:
        post = post.to_dict()
        thread = post['thread_name']
        title_text = post['title']
        body_text = post['content']
        profile_img_url = post['profile_img']
        subreddit_icon_url = 'https://www.redditinc.com/assets/images/site/reddit-logo.png'
        username = post['username']
        image = make_reddit_post_image(thread, title_text, body_text, profile_img_url, subreddit_icon_url, username)
        if image is not None:
            image_saver.save_image(image, thread)

