import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import random


def decode_surrogates(s):
    return s.encode("utf-16", "surrogatepass").decode("utf-16")


class Post:
    def __init__(self, username, profile_img, content, thread_name, title, url):
        self.username = username
        self.profile_img = profile_img
        self.content = content
        self.thread_name = thread_name
        self.title = title
        self.url = url

    def to_dict(self):
        return {
            "username": self.username,
            "profile_img": self.profile_img,
            "content": self.content,
            "thread_name": self.thread_name,
            "title": self.title,
            "url": self.url,
        }


class RedditScraper:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized ")
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        self.saver = DataSaver()

    def get_posts(self, thread_link, max_posts=50, scroll_pause=0.2, max_scrolls=200):
        self.driver.get(thread_link)
        time.sleep(5)

        post_links = set()
        scrolls = 0

        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while len(post_links) < max_posts and scrolls < max_scrolls:
            # Scroll to bottom
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(scroll_pause)

            # Look for new posts
            posts = self.driver.find_elements(By.CSS_SELECTOR, "a.absolute.inset-0")
            for post in posts:
                href = post.get_attribute("href")
                if href and "/comments/" in href:
                    if self.saver.data_exists(href):
                        # print(f"Post {href} already exists, skipping...")
                        continue
                    post_links.add(href)

            # Check if the scroll did anything
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break  # No more content
            last_height = new_height
            scrolls += 1
            print(f"Scroll {scrolls}, collected {len(post_links)} links")

        print(f"Scraped a total of {len(post_links)} post links.")
        return list(post_links)

    def url2thread_name(self, url):
        # https://www.reddit.com/r/AmItheAsshole/comments/1lu69qb/aita_for_pulling_my_daughter_from_soccer_camp_and/
        # extract the AmItheAsshole part
        try:
            thread_name = url.split("https://www.reddit.com/r/")[1].split("/")[0]
            return thread_name
        except:
            pass

        return None

    def get_post_content(self, post_link):
        print("Starting to scrape post:", post_link)
        scrape_start_time = time.time()
        print("Getting to page...")
        self.driver.get(post_link)
        time.sleep(5)

        try:
            read_more_button = self.driver.find_element(
                By.XPATH, "//button[contains(., 'Read more')]"
            )
            read_more_button.click()
            time.sleep(1)  # Let the content expand
        except:
            pass

        # repeatedly scrape content until we get all necessary data
        timeout = 10  # s
        username, profile_img, content, title = None, None, None, None
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if username is None:
                    username = self.driver.find_element(
                        By.CSS_SELECTOR, "a.author-name"
                    ).text
            except:
                pass

            try:
                if profile_img is None:
                    profile_img = self.driver.find_element(
                        By.CSS_SELECTOR, "img.shreddit-subreddit-icon__icon"
                    )
            except:
                pass

            try:
                if content is None:
                    content = self.driver.find_element(By.CSS_SELECTOR, "div.md").text
            except:
                pass

            try:
                if title is None:
                    title = self.driver.find_element(
                        By.CSS_SELECTOR, "h1[id^='post-title-']"
                    ).text
            except:
                pass

            # if all data exists break
            if None not in (username, profile_img, content, title):
                break

        post = Post(
            username=username,
            profile_img=profile_img.get_attribute("src") if profile_img else None,
            content=content,
            thread_name=self.url2thread_name(post_link),
            title=title,
            url=post_link,
        )
        print(f"Scraped {post_link} in {time.time() - scrape_start_time:.2f}s!")
        return post


class DataSaver:
    def __init__(self):
        self.data_folder_path = "reddit_data"
        if not os.path.exists(self.data_folder_path):
            os.makedirs(self.data_folder_path)
        self.file_count = None

    def data_exists(self, post_url):
        files = os.listdir(self.data_folder_path)
        self.file_count = len(files)
        for f in files:
            if ".json" in f:
                with open(os.path.join(self.data_folder_path, f), "r") as file:
                    data = json.load(file)
                    if data.get("url") == post_url:
                        return True
        return False

    def save_post_data(self, post: Post):
        # clean the post content before it gets written
        post.content = decode_surrogates(post.content)
        post.title = decode_surrogates(post.title)

        # check if already exists
        url = post.url
        if self.data_exists(url):
            # print(f"Post {url} already exists, skipping save.")
            return

        data = post.to_dict()
        # make a uuid for this file name
        file_name = (
            "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=20))
            + ".json"
        )
        file_path = os.path.join(self.data_folder_path, file_name)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Saved this post data. There are now ~{self.file_count} posts saved!")

    def get_all_posts(self):
        posts = []
        file_names = os.listdir(self.data_folder_path)
        for file_name in file_names:
            if file_name.endswith(".json"):
                file_path = os.path.join(self.data_folder_path, file_name)
                with open(file_path, "r") as f:
                    data = json.load(f)
                    post = Post(
                        data["username"],
                        data["profile_img"],
                        data["content"],
                        data["thread_name"],
                        data["title"],
                        data["url"],
                    )
                    posts.append(post)
                    print(f"Loaded post {len(posts)} / {len(file_names)}", end="\r")
        return posts


def scrape_thread(thread_url, posts_to_scrape: int, stop_flag):
    posts_scraped = 0
    scraper = RedditScraper()
    data_saver = DataSaver()

    try:
        post_links = scraper.get_posts(thread_url, max_posts=posts_to_scrape)[
            :posts_to_scrape
        ]
        random.shuffle(post_links)

        for post_link in post_links:
            if stop_flag.is_set():
                print(f"[!] Stopping thread for {thread_url}")
                break
            if posts_scraped >= posts_to_scrape:
                break
            post = scraper.get_post_content(post_link)
            data_saver.save_post_data(post)
            posts_scraped += 1

    except Exception as e:
        print(f"Error scraping thread {thread_url}: {e}")


def scrape_all_threads(threads_to_scrape, posts_to_scrape: int, stop_flag):
    threads = []
    for thread in threads_to_scrape:
        try:
            t = threading.Thread(
                target=scrape_thread, args=(thread, posts_to_scrape, stop_flag)
            )
            t.start()
            threads.append(t)
        except Exception as e:
            print(f"[!] Failed to start thread for {thread}: {e}")
    return threads


if __name__ == "__main__":
    threads_to_scrape = [
        "https://www.reddit.com/r/tifu/",
        "https://www.reddit.com/r/AmItheAsshole/",
        "https://www.reddit.com/r/pettyrevenge/",
        "https://www.reddit.com/r/ProRevenge/",
        "https://www.reddit.com/r/raisedbynarcissists/",
        "https://www.reddit.com/r/confession/",
        "https://www.reddit.com/r/offmychest/",
        "https://www.reddit.com/r/offmychest/",
        "https://www.reddit.com/r/MaliciousCompliance/",
        "https://www.reddit.com/r/karen/",
        "https://www.reddit.com/r/TalesFromRetail/",
    ]
    scrape_all_threads(threads_to_scrape, 500)
