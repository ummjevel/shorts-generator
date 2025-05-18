import os
import json
# moviepy는 설치 후 임포트 가능
from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, ColorClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip, AudioClip
import numpy as np
import glob
import re # Import regex for filename parsing
from moviepy.editor import vfx # Import visual effects, including speedx for audio
import logging
import yaml
from datetime import datetime # Import the datetime class

# 기존 logger 설정을 따르거나 기본 로거 사용
try:
    from loguru import logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# Need ContentImageGenerator and TTSGenerator imports - assuming they exist and are importable from src
# Ensure sys.path is set up correctly if these imports fail when running this script directly
try:
    # Assuming these can be imported relative to the project root
    # You might need to adjust sys.path if running this script directly requires it
    from src.content.generator import ContentImageGenerator
    from src.content.tts.generator import TTSGenerator
except ImportError as e:
    logger.error(f"Failed to import ContentImageGenerator or TTSGenerator: {e}. Ensure src directory is in sys.path or adjust imports.")
    # Example sys.path adjustment if needed:
    # import sys
    # # Assuming video/generator.py is in src/video/
    # project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    # sys.path.insert(0, project_root)
    # try:
    #    from src.content.generator import ContentImageGenerator
    #    from src.content.tts.generator import TTSGenerator
    # except ImportError:
    #    logger.error("Failed to import after sys.path adjustment. Exiting.")
    #    exit(1)


class VideoGenerator:
    """
    Generates video clips from a sequence of images and an audio file.
    """

    def __init__(self, output_dir="output/videos"):
        """
        Initializes the VideoGenerator.

        Args:
            output_dir (str): Directory to save the generated videos.
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.debug(f"Created output directory: {self.output_dir}")

    def generate_video(
        self, image_duration_list: list[tuple[str, float]], audio_clip: AudioClip | None, video_filename: str
    ) -> str | None:
        """
        Generates a video from image files with specified durations and an optional audio clip.

        Args:
            image_duration_list (list[tuple[str, float]]): List of tuples where each tuple contains
                                                           (image_file_path: str, duration_in_seconds: float).
            audio_clip (AudioClip | None): The moviepy AudioClip object, or None if no audio.
            video_filename (str): The name for the output video file (without extension).

        Returns:
            str | None: Path to the generated video file, or None if generation failed.
        """
        logger.info(f"Starting Shorts video generation for {video_filename} in {self.output_dir}")

        if not image_duration_list:
            logger.error("No image duration data provided. Cannot generate video.")
            return None

        # 이미지 파일 경로 리스트와 해당 이미지들의 지속 시간 리스트 분리
        image_files = [item[0] for item in image_duration_list]
        durations = [item[1] for item in image_duration_list]

        if len(image_files) != len(durations):
            logger.error(f"Mismatch between number of image files ({len(image_files)}) and durations ({len(durations)}). Cannot generate video.")
            return None

        # Create image sequence clip with specified durations
        logger.info(f"Creating image sequence clip for {video_filename} with {len(image_files)} images.")
        try:
             video_clip = ImageSequenceClip(image_files, durations=durations)
             logger.info(f"Created image sequence clip with total duration {video_clip.duration:.2f} seconds.")
        except Exception as e:
             logger.error(f"Error creating image sequence clip for {video_filename}: {e}")
             return None


        final_clip = video_clip

        if audio_clip:
            # Set the audio of the video clip
            final_clip = video_clip.set_audio(audio_clip)
            logger.info(f"Set audio clip with duration {audio_clip.duration:.2f}s to video clip.")

            # Ensure the video duration matches the audio duration if audio is present
            # The ImageSequenceClip duration should ideally match the sum of durations_in_order, which are based on audio.
            # Set the duration of the final video clip to the duration of the concatenated audio to be safe.
            final_clip = final_clip.set_duration(audio_clip.duration)
            logger.info(f"Final video clip duration for {video_filename}: {final_clip.duration:.2f}s (set to audio duration).")
        else:
             # If no audio, the video duration is the sum of image durations
             final_clip = video_clip.set_duration(video_clip.duration)
             logger.warning(f"No audio clip provided for {video_filename}. Video duration set to total image duration {final_clip.duration:.2f}s.")


        # 최종 영상 파일 경로 설정
        output_filepath = os.path.join(self.output_dir, f"{video_filename}.mp4") # MP4 확장자 사용

        # 최종 영상 파일 저장
        # codec='libx264'는 MP4를 위한 일반적인 코덱입니다.
        # fps=24는 프레임 속도입니다. Shorts에 적합한 설정을 고려해야 합니다.
        # threads=4는 인코딩에 사용할 스레드 수입니다.
        logger.info(f"Writing final video to {output_filepath}...")
        try:
            # Write video file. Using preset='medium' as a balance between speed and quality
            final_clip.write_videofile(output_filepath, codec='libx264', fps=24, threads=4, preset='medium', remove_temp=True) # remove_temp=True to clean up temporary files
            logger.info(f"Successfully generated Shorts video: {output_filepath}")
            return output_filepath
        except Exception as e:
            logger.error(f"An error occurred during video generation for {video_filename}: {e}")
            return None


# Add the updated find_latest_json_data function here (remove the old one if it exists below __init__)
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
            print(f"  - {os.path.basename(f)}") # Use print in example usage
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


if __name__ == "__main__":
    # 예시 사용법 업데이트 (실제 경로 및 데이터 구조에 맞춰 수정 필요)
    logging.basicConfig(level=logging.INFO) # 기본 로거 설정

    # Need ContentImageGenerator and TTSGenerator for image/audio generation in the example
    try:
        # Adjust import based on your project structure if needed
        from src.content.generator import ContentImageGenerator
        from src.content.tts.generator import TTSGenerator
    except ImportError as e:
        logger.error(f"Failed to import ContentImageGenerator or TTSGenerator in __main__ block: {e}. Ensure src directory is in sys.path or adjust imports.")
        exit(1) # Exit if essential modules cannot be imported


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

    logger.info("Running VideoGenerator script directly.")

    config = load_config()
    if not config:
        logger.error("Failed to load config. Exiting.")
        exit()

    output_base_dir = config.get('output', {}).get('base_dir', 'output')
    audio_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('audio_subdir', 'audio'))
    image_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('images_subdir', 'images'))
    video_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('videos_subdir', 'videos')) # For saving test video

    # Use the updated find_latest_json_data to get all latest files
    latest_data_files = find_latest_json_data(output_base_dir)
    if not latest_data_files:
        logger.error("No data files found to process. Exiting.")
        exit()

    total_posts_processed = 0
    total_videos_generated = 0
    # Initialize VideoGenerator once with the base video output directory
    # We will initialize a new VideoGenerator for each post's specific output directory later
    # video_generator_base = VideoGenerator(output_dir=video_base_dir)


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

        logger.info(f"Found {len(posts)} posts in {os.path.basename(data_filepath)}.")

        # Initialize ContentImageGenerator and TTSGenerator for processing posts from this file
        image_generator = ContentImageGenerator(output_dir=image_base_dir) # Image base dir, will set post-specific dir later
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
            current_post_image_output_dir = os.path.join(image_base_dir, post_id)
            post_audio_output_dir = os.path.join(audio_base_dir, post_id)
            post_video_output_dir = os.path.join(video_base_dir, post_id) # Use post_id subdir for video output as well

            os.makedirs(current_post_image_output_dir, exist_ok=True)
            os.makedirs(post_audio_output_dir, exist_ok=True)
            os.makedirs(post_video_output_dir, exist_ok=True)


            # --- Generate Audio for the Post ---
            audio_segment_map = {} # Map segment identifier to audio filepath
            # Reuse existing audio generation logic from main.py structure


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
            image_generator.current_post_index = post_index # Ensure index is set for filename for this post
            post_image_files = image_generator.post_to_images(post_data) # Generate images for this single post
            logger.info(f"Generated {len(post_image_files)} image files for post {post_id}.")


            # --- Prepare Data for Video Generation for THIS Post ---
            image_duration_list = [] # List of (image_filepath, duration) tuples for this post
            processed_audio_clips = [] # List of speed-adjusted AudioClip objects for this post


            audio_speed_factor = config.get('content', {}).get('tts', {}).get('speed_factor', 1.0)
            logger.info(f"Applying audio speed factor: {audio_speed_factor}")

            # Sort the audio segments by identifier (e.g., 'title_1', 'body_1', 'comment1_1', ...)
            # Use the sorting logic defined previously
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
                         matching_images = [img_path for img_path in post_image_files if f"_{identifier}.png" in os.path.basename(img_path)]

                         if matching_images:
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


            # --- Video Generation for THIS Post ---
            if not image_duration_list or not processed_audio_clips:
                logger.warning(f"Skipping video generation for post {post_id} due to missing images or audio clips.")
            else:
                try:
                    # Concatenate all processed audio clips for this post
                    if processed_audio_clips:
                        logger.info(f"Concatenating {len(processed_audio_clips)} audio clips for post {post_id}.")
                        final_audio_clip = concatenate_videoclips(processed_audio_clips, method="compose")
                        logger.info(f"Final audio clip duration for post {post_id}: {final_audio_clip.duration:.2f}s")

                        # Create image clip sequence with specific durations
                        images_in_order = [img_path for img_path, duration in image_duration_list]
                        durations_in_order = [duration for img_path, duration in image_duration_list]


                        if not images_in_order or not durations_in_order or len(images_in_order) != len(durations_in_order):
                            logger.error(f"Mismatch in image and duration lists for post {post_id}. Cannot create video.")
                        else:
                             logger.info(f"Creating image sequence clip for post {post_id} with {len(images_in_order)} images.")
                             # Create the image clip sequence with specified durations
                             image_clip_sequence = ImageSequenceClip(images_in_order, durations=durations_in_order)

                             # Call the VideoGenerator.generate_video method for this post
                             video_filename_base = post_id # Base filename for this post

                             # Initialize VideoGenerator for THIS post's directory
                             video_gen_for_post = VideoGenerator(output_dir=post_video_output_dir)
                             generated_video_path = video_gen_for_post.generate_video(image_duration_list, final_audio_clip, video_filename_base) # Pass the base filename


                             if generated_video_path:
                                 logger.info(f"Successfully generated video for post {post_id} at: {generated_video_path}")
                                 total_videos_generated += 1
                             else:
                                 logger.error(f"Failed to generate video for post {post_id}.")
                        else: # if not images_in_order ...
                            logger.error(f"Could not create image sequence clip for post {post_id} due to image/duration mismatch.")

                    else: # if not processed_audio_clips
                        logger.warning(f"No processed audio clips available for post {post_id}. Cannot add audio to video.")
                        # Optionally write video without audio, or skip
                        # Create image clip sequence with specific durations even without audio
                        images_in_order = [img_path for img_path, duration in image_duration_list]
                        durations_in_order = [duration for img_path, duration in image_duration_list]
                        if images_in_order and durations_in_order and len(images_in_order) == len(durations_in_order):
                             logger.info(f"Writing video without audio for post {post_id}...")
                             image_clip_sequence = ImageSequenceClip(images_in_order, durations=durations_in_order)
                             video_gen_for_post = VideoGenerator(output_dir=post_video_output_dir) # Initialize for THIS post's directory
                             video_filename_base = f"{post_id}_shorts_no_audio"
                             generated_video_path = video_gen_for_post.generate_video(image_duration_list, None, video_filename_base) # Pass None for audio_clip

                             if generated_video_path:
                                 logger.warning(f"Generated video WITHOUT audio for post {post_id} at: {generated_video_path}")
                             else:
                                  logger.error(f"Failed to generate video without audio for post {post_id}.")
                        else:
                            logger.warning(f"Skipping video generation without audio for post {post_id} due to missing images or duration mismatch.")


                except Exception as e:
                    logger.error(f"An error occurred during video generation for post {post_id}: {e}")

    logger.info("\nVideo generation script finished.")
    logger.info(f"Total posts processed: {total_posts_processed}")
    logger.info(f"Total videos generated: {total_videos_generated}")

    # Note: Temporary image files (if any were created during image generation test runs) are NOT cleaned up here
    # as we are now using images from output/images. The cleanup logic in ContentImageGenerator's
    # example usage or a separate cleanup script should handle that if needed. 