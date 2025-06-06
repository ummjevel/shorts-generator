# src/content/tts/test_generator.py

import os
import json # Import json to read the data file
import re # Import re for sentence splitting
from loguru import logger # Keep logger import for potential future use or consistency
import yaml # To read config for output directory
import sys
import glob
from datetime import datetime # Import the datetime class

# Let's make it robust by finding the project root based on a known file like requirements.txt or src/main.py
current_dir = os.path.dirname(os.path.abspath(__file__))
# Corrected path calculation: need to go up three directories from src/content/tts/ to reach project root
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
sys.path.insert(0, project_root)

try:
    from src.content.tts.generator import TTSGenerator
    from src.content.generator import ContentImageGenerator # URL 제거 함수를 위해 필요
except ImportError as e:
    print(f"Failed to import modules: {e}")
    print(f"Attempted to add '{project_root}' to sys.path. Current sys.path: {sys.path}")
    sys.exit(1)

# Assuming config file is at the project root
CONFIG_PATH = "config/config.yaml"

def load_config(config_path=CONFIG_PATH):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"Config loaded from {config_path}")
        return config
    except FileNotFoundError:
        print(f"Config file not found at {config_path}")
        return None
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}")
        return None

def find_latest_json_data(base_output_dir="output"):
    """Find the latest JSON data file in the base output directory based on date in filename."""
    # Assuming JSON data is saved directly in the base output dir based on previous tests
    output_json_files = glob.glob(os.path.join(base_output_dir, "*.json"))
    if not output_json_files:
        print(f"No Reddit data JSON files found in {base_output_dir}.")
        return None

    latest_file = None
    latest_date = None
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})', # YYYY-MM-DD
        r'(\d{8})' # YYYYMMDD
    ]

    for filepath in output_json_files:
        filename = os.path.basename(filepath)
        current_file_date = None

        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if match:
                date_str = match.group(1)
                try:
                    # Try parsing with different formats
                    if '-' in date_str:
                        current_file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    else:
                         current_file_date = datetime.strptime(date_str, '%Y%m%d').date()
                    break # Found and parsed a date, no need to try other patterns
                except ValueError:
                    continue # Mismatch with date format, try next pattern

        if current_file_date:
            if latest_date is None or current_file_date > latest_date:
                latest_date = current_file_date
                latest_file = filepath
                print(f"Found potential latest file: {filename} with date {latest_date}") # Debug print
        else:
            print(f"Warning: Could not find or parse date from filename: {filename}") # Debug print

    if latest_file:
        print(f"Using latest data file based on filename date: {os.path.basename(latest_file)}")
        return latest_file
    else:
        print(f"No JSON data files with parsable dates found in {base_output_dir}. Fallback to ctime.")
        # Fallback to using creation time if no date found in filenames
        if output_json_files:
             latest_json_file_ctime = max(output_json_files, key=os.path.getctime)
             print(f"Using latest data file based on creation time: {os.path.basename(latest_json_file_ctime)}")
             return latest_json_file_ctime
        else:
            return None # Should not happen based on initial check, but for safety

def main():
    print("TTS Test Script Started.")

    config = load_config()
    if not config:
        print("Failed to load configuration. Exiting.")
        return

    # Define base output directories from config
    output_base_dir = config.get('output', {}).get('base_dir', 'output')
    audio_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('audio_subdir', 'audio'))

    latest_data_file = find_latest_json_data(output_base_dir)
    if not latest_data_file:
        print("No data file found to test with. Exiting.")
        return

    # Load the collected data
    try:
        with open(latest_data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON file {latest_data_file}: {e}")
        return

    # Get the first post and its ID for directory naming
    posts = []
    if isinstance(data, list):
        posts = data
    elif isinstance(data, dict) and "posts" in data and isinstance(data["posts"], list):
        posts = data["posts"]

    if not posts:
        print(f"No post data found in {latest_data_file}. Exiting.")
        return

    # Initialize TTS Generator - assuming it needs config path
    tts_generator = TTSGenerator(config_path=CONFIG_PATH)

    if not hasattr(tts_generator, 'generate_audio') or not callable(tts_generator.generate_audio):
         print("TTSGenerator does not have a callable generate_audio method. Exiting.")
         return

    generated_count = 0

    # --- Process each post in the data ---
    for post_index, post_data in enumerate(posts):
        post_id = post_data.get("id")

        if not post_id:
            print(f"Skipping post at index {post_index} with no id.")
            continue

        print(f"\nProcessing Post ID: {post_id}")

        # Define the specific audio output directory for this post
        post_audio_output_dir = os.path.join(audio_base_dir, post_id)
        os.makedirs(post_audio_output_dir, exist_ok=True)
        print(f"Audio for post {post_id} will be saved to: {post_audio_output_dir}")

        # --- Generate Audio for Title ---
        title_text = post_data.get("title", "").strip()
        if title_text:
            cleaned_text = ContentImageGenerator._remove_urls(title_text)
            # Ensure output filename includes post_id for uniqueness across posts
            output_filename = f"{post_id}_title_1.mp3"
            output_filepath = os.path.join(post_audio_output_dir, output_filename)
            print(f"  Generating audio for title of post {post_id}...")
            if tts_generator.generate_audio(cleaned_text, output_filepath):
                print(f"  Successfully generated: {output_filename}")
                generated_count += 1
            else:
                print(f"  Failed to generate audio for title of post {post_id}.")

        # --- Generate Audio for Body ---
        body_text = post_data.get("body", post_data.get('selftext', '')).strip()
        if body_text:
            cleaned_text = ContentImageGenerator._remove_urls(body_text)
            # Assuming body is a single part for audio generation in test
            # Ensure output filename includes post_id
            output_filename = f"{post_id}_body_1.mp3"
            output_filepath = os.path.join(post_audio_output_dir, output_filename)
            print(f"  Generating audio for body of post {post_id}...")
            if tts_generator.generate_audio(cleaned_text, output_filepath):
                print(f"  Successfully generated: {output_filename}")
                generated_count += 1
            else:
                print(f"  Failed to generate audio for body of post {post_id}.")

        # --- Generate Audio for Comments (Top N) ---
        comments = sorted(post_data.get('comments', []), key=lambda c: c.get('score', 0), reverse=True)
        max_comments_to_test = config.get('reddit', {}).get('max_comments_per_post', 3) # Use config or a default test limit
        comments_to_process = comments[:max_comments_to_test]

        if comments_to_process:
            print(f"  Processing top {len(comments_to_process)} comments for post {post_id}...")
            for c_idx, comment in enumerate(comments_to_process):
                 comment_author = comment.get('author', '') or '[Deleted]'
                 comment_body = comment.get('body', '') or ''
                 comment_text = f"{comment_author}: {comment_body}".strip()

                 if comment_text:
                      cleaned_text = ContentImageGenerator._remove_urls(comment_text)
                      # Assuming each comment is a single part for audio generation in test
                      # Ensure output filename includes post_id
                      output_filename = f"{post_id}_comment{c_idx+1}_1.mp3"
                      output_filepath = os.path.join(post_audio_output_dir, output_filename)
                      print(f"    Generating audio for comment {c_idx+1} of post {post_id}...")
                      if tts_generator.generate_audio(cleaned_text, output_filepath):
                           print(f"    Successfully generated: {output_filename}")
                           generated_count += 1
                      else:
                           print(f"    Failed to generate audio for comment {c_idx+1} of post {post_id}.")

    print(f"\nTTS Test Script Finished. Total audio files generated across all posts: {generated_count}")

if __name__ == "__main__":
    main() 