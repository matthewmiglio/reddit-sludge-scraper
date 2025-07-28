import tkinter as tk
from tkinter import filedialog
import threading
import random
import os

from scraper import scrape_all_threads
from video_maker import create_all_stacked_reddit_scroll_videos


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Slop Media Machine")
        self.geometry("270x420")
        self.configure(bg="#1e1e1e")

        self.stats = {
            "posts_scraped": 0,
            "videos_created": 0,
        }

        # Container for all pages
        self.container = tk.Frame(self, bg="#1e1e1e")
        self.container.pack(fill="both", expand=True)

        # Persistent Stats Bar
        self.stats_bar = tk.Label(
            self, text="", bg="#2e2e2e", fg="lightgray", anchor="w", padx=10
        )
        self.stats_bar.pack(side="bottom", fill="x")

        # Setup all frames
        self.frames = {}
        for F in (MainMenu, ScraperPage, SlopGenPage):
            frame = F(parent=self.container, controller=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(MainMenu)
        self.refresh_stats()

    def show_frame(self, page_class):
        self.frames[page_class].tkraise()

    def refresh_stats(self):
        scraped_posts_folder = r"reddit_data"
        final_videos_folder = r"final_vids"

        scraped_posts_count = (
            len(os.listdir(scraped_posts_folder))
            if os.path.exists(scraped_posts_folder)
            else 0
        )
        final_videos_count = (
            len(os.listdir(final_videos_folder))
            if os.path.exists(final_videos_folder)
            else 0
        )

        # Simulated stat updates
        self.stats["posts_scraped"] = scraped_posts_count
        self.stats["videos_created"] = final_videos_count

        # Update persistent stats bar
        self.stats_bar.config(
            text=f"📊 Posts Scraped: {self.stats['posts_scraped']} | 🎬 Videos Made: {self.stats['videos_created']}"
        )

        self.after(10000, self.refresh_stats)  # Refresh every 10s


class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1e1e1e")
        self.controller = controller

        tk.Label(
            self,
            text="Slop Media Machine",
            font=("Helvetica", 20),
            bg="#1e1e1e",
            fg="white",
        ).pack(pady=20)

        tk.Label(self, text="Choose a mode below", bg="#1e1e1e", fg="gray").pack(pady=5)

        tk.Button(
            self,
            text="📥 Reddit Scraper",
            command=lambda: controller.show_frame(ScraperPage),
            width=30,
        ).pack(pady=10)

        tk.Button(
            self,
            text="🎬 Slop Video Generator",
            command=lambda: controller.show_frame(SlopGenPage),
            width=30,
        ).pack(pady=10)


class ScraperPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1e1e1e")
        self.controller = controller
        self.scrape_thread = None  # Thread handle placeholder
        self.stop_flag = threading.Event()

        tk.Label(
            self,
            text="Reddit Scraper",
            font=("Helvetica", 18),
            bg="#1e1e1e",
            fg="white",
        ).pack(pady=10)

        tk.Label(
            self,
            text="Scrape Reddit threads for short storytelling content",
            bg="#1e1e1e",
            fg="gray",
        ).pack(pady=5)

        self.thread_count = tk.IntVar(value=500)

        tk.Label(self, text="Posts per thread:", bg="#1e1e1e", fg="white").pack()
        tk.Entry(self, textvariable=self.thread_count, width=10).pack(pady=5)

        tk.Button(self, text="Start Scraping", command=self.start_scraper).pack(pady=5)
        tk.Button(self, text="Stop Scraping", command=self.stop_scraper).pack(pady=5)
        tk.Button(
            self, text="⬅ Back to Main", command=lambda: controller.show_frame(MainMenu)
        ).pack(pady=10)

        self.status_label = tk.Label(self, text="", bg="#1e1e1e", fg="lightgreen")
        self.status_label.pack(pady=10)

    def start_scraper(self):
        def run():
            self.stop_flag.clear()
            self.status_label.config(text="Scraping started...")
            try:
                threads = [
                    "https://www.reddit.com/r/tifu/",
                    "https://www.reddit.com/r/AmItheAsshole/",
                    "https://www.reddit.com/r/pettyrevenge/",
                    "https://www.reddit.com/r/ProRevenge/",
                    "https://www.reddit.com/r/raisedbynarcissists/",
                    "https://www.reddit.com/r/confession/",
                    "https://www.reddit.com/r/offmychest/",
                    "https://www.reddit.com/r/MaliciousCompliance/",
                    "https://www.reddit.com/r/karen/",
                    "https://www.reddit.com/r/TalesFromRetail/",
                    "https://www.reddit.com/r/dating/",
                    "https://www.reddit.com/r/dating_advice/",
                    "https://www.reddit.com/r/BreakUps/",
                    "https://www.reddit.com/r/TwoXChromosomes/",
                    "https://www.reddit.com/r/FemaleDatingStrategy/",
                ]
                scrape_all_threads(threads, self.thread_count.get(), self.stop_flag)
                self.status_label.config(text="Scraping complete or stopped.")
            except Exception as e:
                self.status_label.config(text=f"Error: {e}")

        self.scrape_thread = threading.Thread(target=run)
        self.scrape_thread.start()

    def stop_scraper(self):
        self.stop_flag.set()
        self.status_label.config(text="Stopping scrape threads...")


class SlopGenPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1e1e1e")
        self.controller = controller

        tk.Label(
            self,
            text="Slop Video Generator",
            font=("Helvetica", 18),
            bg="#1e1e1e",
            fg="white",
        ).pack(pady=10)

        tk.Label(
            self,
            text="Generate vertical sludge videos\nfrom scraped Reddit posts",
            bg="#1e1e1e",
            fg="gray",
        ).pack(pady=5)

        tk.Button(self, text="Start Generating", command=self.start_generation).pack(
            pady=10
        )
        tk.Button(
            self, text="⬅ Back to Main", command=lambda: controller.show_frame(MainMenu)
        ).pack(pady=10)

        self.status_label = tk.Label(self, text="", bg="#1e1e1e", fg="lightgreen")
        self.status_label.pack(pady=10)

    def start_generation(self):
        def run():
            self.status_label.config(text="Video generation started...")
            try:
                create_all_stacked_reddit_scroll_videos(output_dir=r"final_vids")
                self.status_label.config(text="All videos created!")
            except Exception as e:
                self.status_label.config(text=f"Error: {e}")

        threading.Thread(target=run).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
