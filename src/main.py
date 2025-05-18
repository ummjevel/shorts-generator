import os
import glob
import json
import yaml
from loguru import logger
from datetime import datetime
import re
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip

# Import modules
from src.reddit.collector import RedditCollector
from src.content.generator import ContentImageGenerator
from src.content.tts.generator import TTSGenerator
from src.video.generator import VideoGenerator

# Set up logging
try:
    logger.add("logs/shorts_agent.log", rotation="1 MB")
except Exception as e:
    print(f"Error setting up logger: {e}. Proceeding without detailed file logging.")
    # Basic logging fallback if loguru configuration fails
    class DummyLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")
    logger = DummyLogger()

logger.info("Shorts Agent Main Script Started.")

def load_config(config_path="config/config.yaml"):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Config loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading config file {config_path}: {e}")
        return None

def find_latest_json_data(base_output_dir="output"):
    """Find all JSON data files in the base output directory that have the latest date in their filename."""
    output_json_files = glob.glob(os.path.join(base_output_dir, "*.json"))
    if not output_json_files:
        logger.warning(f"No Reddit data JSON files found in {base_output_dir}.")
        return [] # Return empty list if no files

    latest_date = None
    date_to_files_map = {} # Map date objects to a list of file paths

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
                    if '-' in date_str:
                        current_file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    else:
                        current_file_date = datetime.strptime(date_str, '%Y%m%d').date()
                    break # Found and parsed a date
                except ValueError:
                    continue # Mismatch, try next pattern

        if current_file_date:
            if latest_date is None or current_file_date > latest_date:
                latest_date = current_file_date
            date_to_files_map.setdefault(current_file_date, []).append(filepath)
        else:
            logger.warning(f"Could not find or parse date from filename: {filename}. This file will be ignored unless it's the only file and date parsing fails for all.") # Adjusted warning

    if latest_date:
        # Return all files associated with the latest date
        latest_files = date_to_files_map[latest_date]
        logger.info(f"Found {len(latest_files)} file(s) with the latest date ({latest_date}):")
        for f in latest_files:
            logger.info(f"  - {os.path.basename(f)}")
        return latest_files
    else:
        logger.warning(f"No JSON data files with parsable dates found in {base_output_dir}. Falling back to finding the single latest file by ctime.")
        # Fallback to using creation time if no date found in any filenames
        if output_json_files:
            # Return a list containing the single latest file by ctime
            latest_json_file_ctime = max(output_json_files, key=os.path.getctime)
            logger.info(f"Using latest data file based on creation time: {os.path.basename(latest_json_file_ctime)}")
            return [latest_json_file_ctime] # Return a list
        else:
            return [] # Should not happen, but for safety

def main():
    logger.info("Loading configuration...")
    config = load_config()
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        return

    # Output directories (should be in config) - using hardcoded defaults for now
    output_base_dir = config.get('output', {}).get('base_dir', 'output')
    reddit_data_dir = os.path.join(output_base_dir, config.get('output', {}).get('reddit_data_subdir', 'reddit_data'))
    image_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('images_subdir', 'images'))
    audio_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('audio_subdir', 'audio'))
    video_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('videos_subdir', 'videos'))
    
    os.makedirs(reddit_data_dir, exist_ok=True)
    os.makedirs(image_base_dir, exist_ok=True)
    os.makedirs(audio_base_dir, exist_ok=True)
    os.makedirs(video_base_dir, exist_ok=True)

    # --- Step 1: Collect Reddit Data ---
    logger.info("Starting Reddit data collection...")
    reddit_config = config.get('reddit', {})
    # Pass output_dir to RedditCollector if it saves data internally, or handle saving here
    collector = RedditCollector(config=reddit_config) # Assuming collector uses config internally for subreddits etc.
    
    # collector.collect_and_save_subreddit() # Call the collection method - needs parameters or internal config
    # Assuming collect_and_save_subreddit saves to reddit_data_dir based on its implementation
    # For now, let's assume data is saved to a JSON file in output_base_dir (based on previous tests)
    # We'll need to clarify how the collector is used and where it saves.
    logger.warning("Reddit data collection step is a placeholder. Assuming data is already in output/*.json")

    # --- Step 2: Process Latest Collected Data (Images and Audio) and Generate Videos ---
    logger.info("Processing latest collected data files and generating videos...")

    latest_data_files = find_latest_json_data(output_base_dir) # Get a list of files
    if not latest_data_files:
        logger.error("No data files found to process. Exiting.")
        return

    total_posts_processed = 0
    total_videos_generated = 0

    # --- Loop through each latest data file ---
    for data_filepath in latest_data_files:
        logger.info(f"\nProcessing data file: {os.path.basename(data_filepath)}")

        # Load the collected data from the current file
        try:
            with open(data_filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON file {data_filepath}: {e}. Skipping this file.")
            continue # Skip to the next file

        posts = []
        if isinstance(data, list):
            posts = data
        elif isinstance(data, dict) and "posts" in data and isinstance(data["posts"], list):
            posts = data["posts"]
        else:
            logger.error(f"Unexpected data format in {data_filepath}. Expected a list or a dictionary with a 'posts' key containing a list. Skipping this file.")
            continue # Skip to the next file

        if not posts:
            logger.warning(f"No post data found in {data_filepath}. Skipping this file.")
            continue # Skip to the next file

        logger.info(f"Found {len(posts)} posts in {os.path.basename(data_filepath)}. ")

        # Initialize generators for this data file if needed (or reuse if stateless/thread-safe)
        # Re-initializing generators per file might be safer depending on their implementation
        image_generator = ContentImageGenerator(output_dir=image_base_dir) # Image base dir
        tts_generator = TTSGenerator(config_path="config/config.yaml")

        # --- Loop through each post in the current data file ---
        for post_index, post_data in enumerate(posts):
            post_id = post_data.get("id")
            if not post_id:
                logger.warning(f"Skipping post at index {post_index} in {os.path.basename(data_filepath)} with no id.")
                continue

            logger.info(f"\nProcessing Post Index: {post_index}, Post ID: {post_id} from {os.path.basename(data_filepath)}")
            total_posts_processed += 1

            # Define output directories for this specific post
            # Using post_id for subdirectory for organization
            current_post_image_output_dir = os.path.join(image_base_dir, post_id)
            post_audio_output_dir = os.path.join(audio_base_dir, post_id)
            post_video_output_dir = os.path.join(video_base_dir, post_id)

            os.makedirs(current_post_image_output_dir, exist_ok=True)
            os.makedirs(post_audio_output_dir, exist_ok=True)
            os.makedirs(post_video_output_dir, exist_ok=True)

            # --- Generate Audio for the Post ---
            audio_segment_map = {} # Map segment identifier to audio filepath
            # Reuse existing audio generation logic

            # Generate audio for title
            title_text = post_data.get("title", "")
            if title_text:
                title_audio_filepath = os.path.join(post_audio_output_dir, f"title_1.mp3")
                logger.info(f"Generating audio for title...")
                if tts_generator.generate_audio(title_text, title_audio_filepath):
                    audio_segment_map['title_1'] = title_audio_filepath
                else:
                    logger.warning("Failed to generate audio for title.")

            # Generate audio for body
            body_text = post_data.get("body", "")
            if body_text:
                body_audio_filepath = os.path.join(post_audio_output_dir, f"body_1.mp3")
                logger.info(f"Generating audio for body...")
                if tts_generator.generate_audio(body_text, body_audio_filepath):
                    audio_segment_map['body_1'] = body_audio_filepath
                else:
                    logger.warning("Failed to generate audio for body.")

            # Generate audio for comments
            sorted_comments = sorted(post_data.get('comments', []), key=lambda c: c.get('score', 0), reverse=True)
            max_comments_per_post = config.get('reddit', {}).get('max_comments_per_post', 5)
            comments_to_process = sorted_comments[:max_comments_per_post]

            if comments_to_process:
                logger.info(f"Generating audio for top {len(comments_to_process)} comments...")
                for c_idx, comment in enumerate(comments_to_process):
                    comment_author = comment.get('author', '') or '[Deleted]'
                    comment_body = comment.get('body', '') or ''
                    comment_text = f"{comment_author}: {comment_body}"
                    comment_audio_filepath = os.path.join(post_audio_output_dir, f"comment{c_idx+1}_1.mp3")
                    if tts_generator.generate_audio(comment_text, comment_audio_filepath):
                        audio_segment_map[f'comment{c_idx+1}_1'] = comment_audio_filepath
                    else:
                        logger.warning(f"Failed to generate audio for comment {c_idx+1}.")

            # --- Generate Images for the Post ---
            # The image generator needs the specific output dir for this post
            image_generator.output_dir = current_post_image_output_dir # Set output dir for this post
            image_generator.current_post_index = post_index # Ensure index is set for filename
            post_image_files = image_generator.post_to_images(post_data) # Generate images for this single post
            logger.info(f"Generated {len(post_image_files)} image files for post {post_id}.")

            # --- Prepare Data for Video Generation ---
            image_duration_list = [] # List of (image_filepath, duration) tuples
            processed_audio_clips = [] # List of speed-adjusted AudioClip objects

            audio_speed_factor = config.get('content', {}).get('tts', {}).get('speed_factor', 1.0)
            logger.info(f"Applying audio speed factor: {audio_speed_factor}")

            # Sort the audio segments by identifier (e.g., 'title_1', 'body_1', 'comment1_1', ...)
            # Use the sorting logic defined previously in main.py
            def sort_audio_segments(item):
                identifier, filepath = item
                filename = os.path.basename(filepath)
                if filename.startswith('title_'): return 0
                if filename.startswith('body_'): return 1
                comment_match = re.match(r'comment(\d+)_(\d+)', filename)
                if comment_match:
                    return (2 + int(comment_match.group(1)), int(comment_match.group(2)))
                comment_simple_match = re.match(r'comment(\d+)', filename)
                if comment_simple_match:
                    return (2 + int(comment_simple_match.group(1)), 0)
                return (999, 0)

            sorted_audio_segments_items = sorted(audio_segment_map.items(), key=sort_audio_segments)

            # Load sorted audio clips, apply speed factor, and get durations
            for identifier, audio_path in sorted_audio_segments_items:
                if os.path.exists(audio_path):
                    try:
                        clip = AudioFileClip(audio_path)
                        logger.debug(f"Loaded audio clip for {identifier} with original duration {clip.duration:.2f}s from {audio_path}")

                        if audio_speed_factor != 1.0:
                            speed_adjusted_clip = clip.fx(vfx.speedx, factor=audio_speed_factor)
                            logger.debug(f"Applied speed factor {audio_speed_factor} to {identifier}. New duration: {speed_adjusted_clip.duration:.2f}s")
                        else:
                            speed_adjusted_clip = clip

                        processed_audio_clips.append(speed_adjusted_clip) # Store the adjusted clip object

                        # Get the duration from the speed-adjusted clip
                        adjusted_duration = speed_adjusted_clip.duration

                        # Find the corresponding image(s) for this audio segment
                        # Assuming image filenames contain the identifier (e.g., post_[index]_[post_id]_title_1.png)
                        # We need to match the identifier from the audio segment map.
                        matching_images = [img_path for img_path in post_image_files if f"_{identifier}.png" in os.path.basename(img_path)]

                        if matching_images:
                            # Assuming one image per audio segment for simplicity, or distribute duration if multiple
                            # For now, let's assume one primary image per segment. If multiple match, use the first?
                            # A more robust mapping might be needed depending on how images are named/generated.
                            # Let's associate the duration with ALL matching images for now, they'll be shown sequentially.
                            # Or, ideally, the image generator creates distinct images linked to segments.
                            # Let's refine: assume images are named e.g., post_0_post_id_title_1.png, post_0_post_id_comment1_1.png etc.
                            # So, we look for an image filename containing _[identifier].png

                            # If there are multiple images for a single audio segment, we should divide the duration among them.
                            num_matching_images = len(matching_images)
                            duration_per_matching_image = adjusted_duration / num_matching_images if num_matching_images > 0 else 0

                            for img_path in matching_images:
                                image_duration_list.append((img_path, duration_per_matching_image))
                                logger.debug(f"Mapped image {os.path.basename(img_path)} to audio {identifier} with duration {duration_per_matching_image:.2f}s")
                        else:
                            logger.warning(f"No matching image found for audio segment {identifier} for post {post_id}. This audio segment will not have a corresponding image display time.")

                    except Exception as e:
                        logger.error(f"Error processing audio clip {audio_path} for identifier {identifier}: {e}")
                else:
                    logger.warning(f"Audio file not found at {audio_path} for identifier {identifier}.")

            # --- Video Generation for the Post ---
            if not image_duration_list or not processed_audio_clips:
                logger.warning(f"Skipping video generation for post {post_id} due to missing images or audio clips.")
            else:
                try:
                    # Create image clip sequence with specific durations
                    # Need sorted list of image paths and their durations
                    # The image_duration_list is already intended to be in display order based on audio segment order
                    images_in_order = [img_path for img_path, duration in image_duration_list]
                    durations_in_order = [duration for img_path, duration in image_duration_list]

                    if not images_in_order or not durations_in_order or len(images_in_order) != len(durations_in_order):
                        logger.error(f"Mismatch in image and duration lists for post {post_id}. Cannot create video.")
                    else:
                        logger.info(f"Creating image sequence clip for post {post_id} with {len(images_in_order)} images.")
                        # Create the image clip sequence with specified durations
                        image_clip_sequence = ImageSequenceClip(images_in_order, durations=durations_in_order)

                        # Concatenate all processed audio clips for this post
                        if processed_audio_clips:
                            logger.info(f"Concatenating {len(processed_audio_clips)} audio clips for post {post_id}.")
                            final_audio_clip = concatenate_videoclips(processed_audio_clips, method="compose") # method="compose" handles overlaps gracefully
                            logger.info(f"Final audio clip duration for post {post_id}: {final_audio_clip.duration:.2f}s")

                            # Set the audio of the image sequence clip
                            final_video_clip = image_clip_sequence.set_audio(final_audio_clip)

                            # Ensure the video duration matches the audio duration
                            # The ImageSequenceClip duration should ideally match the sum of durations_in_order, which are based on audio.
                            # Set the duration of the final video clip to the duration of the concatenated audio to be safe.
                            final_video_clip = final_video_clip.set_duration(final_audio_clip.duration)
                            logger.info(f"Final video clip duration for post {post_id}: {final_video_clip.duration:.2f}s")

                            # Define output path for the video for this post
                            video_output_filepath = os.path.join(post_video_output_dir, f"{post_id}_shorts.mp4") # Unique name per post
                            logger.info(f"Writing final video for post {post_id} to {video_output_filepath}...")

                            # Write the final video file
                            # codec='libx264', fps=24, threads=4 are reasonable defaults for MP4
                            final_video_clip.write_videofile(video_output_filepath, codec='libx264', fps=24, threads=4)
                            logger.info(f"Successfully generated video for post {post_id}.")
                            total_videos_generated += 1
                        else:
                            logger.warning(f"No processed audio clips available for post {post_id}. Cannot add audio to video.")
                            # Optionally write video without audio, or skip
                            logger.info(f"Writing video without audio for post {post_id}...")
                            video_output_filepath = os.path.join(post_video_output_dir, f"{post_id}_shorts_no_audio.mp4")
                            image_clip_sequence.write_videofile(video_output_filepath, codec='libx264', fps=24, threads=4)
                            logger.warning(f"Generated video without audio for post {post_id}.")

                except Exception as e:
                    logger.error(f"An error occurred during video generation for post {post_id}: {e}")

    logger.info("\nMain script finished.")
    logger.info(f"Total posts processed: {total_posts_processed}")
    logger.info(f"Total videos generated: {total_videos_generated}")

if __name__ == "__main__":
    main() 