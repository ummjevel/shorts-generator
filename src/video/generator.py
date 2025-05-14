import os
from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, ColorClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip, AudioClip
import numpy as np
import glob
import json
import re # Import regex for filename parsing
from moviepy.editor import vfx # Import visual effects, including speedx for audio
import logging
import yaml

# 기존 logger 설정을 따르거나 기본 로거 사용
try:
    from loguru import logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

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
        self, image_duration_list: list[tuple[str, float]], audio_clip: AudioClip, video_filename: str
    ):
        """
        Generates a video from image files with specified durations and an audio clip.

        Args:
            image_duration_list (list[tuple[str, float]]): List of tuples where each tuple contains
                                                           (image_file_path: str, duration_in_seconds: float).
            audio_clip (AudioClip): The moviepy AudioClip object.
            video_filename (str): The name for the output video file (without extension).
        
        Returns:
            str: Path to the generated video file.
        """
        logger.info(f"Starting Shorts video generation for {video_filename}")

        if not image_duration_list:
            logger.error("No image duration data provided. Cannot generate video.")
            return None

        if not audio_clip:
            logger.error("No final audio clip provided. Cannot generate video.")
            return None

        # 이미지 파일 경로 리스트와 해당 이미지들의 지속 시간 리스트 분리
        image_files = [item[0] for item in image_duration_list]
        durations = [item[1] for item in image_duration_list]

        if len(image_files) != len(durations):
            logger.error(f"Mismatch between number of image files ({len(image_files)}) and durations ({len(durations)}). Cannot generate video.")
            return None

        total_image_duration = sum(durations)
        audio_duration = audio_clip.duration

        # 이미지 시퀀스 클립 생성
        # durations 인자로 각 이미지의 표시 시간을 설정합니다.
        video_clip = ImageSequenceClip(image_files, durations=durations)
        logger.info(f"Created image sequence clip with total duration {video_clip.duration:.2f} seconds.")

        # 오디오 클립을 영상 클립에 설정
        final_clip = video_clip.set_audio(audio_clip)

        # 최종 영상 파일 경로 설정
        output_filepath = os.path.join(self.output_dir, f"{video_filename}.mp4") # MP4 확장자 사용

        # 최종 영상 파일 저장
        # codec='libx264'는 MP4를 위한 일반적인 코덱입니다.
        # fps=24는 프레임 속도입니다. Shorts에 적합한 설정을 고려해야 합니다.
        # threads=4는 인코딩에 사용할 스레드 수입니다.
        logger.info(f"Writing final video to {output_filepath}...")
        try:
            # Write video file. Using preset='medium' as a balance between speed and quality
            final_clip.write_videofile(output_filepath, codec='libx264', fps=24, threads=4, preset='medium')
            logger.info(f"Successfully generated Shorts video: {output_filepath}")
            return output_filepath
        except Exception as e:
            logger.error(f"An error occurred during video generation: {e}")
            return None

# Example usage (will be removed or updated later)
if __name__ == "__main__":
    # 예시 사용법 업데이트 (실제 경로 및 데이터 구조에 맞춰 수정 필요)
    logging.basicConfig(level=logging.INFO) # 기본 로거 설정

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
        """Find the latest JSON data file in the base output directory."""
        output_json_files = glob.glob(os.path.join(base_output_dir, "*.json"))
        if not output_json_files:
            logger.error(f"No Reddit data JSON files found in {base_output_dir}.")
            return None

        latest_json_file = max(output_json_files, key=os.path.getctime)
        logger.info(f"Using latest data file: {latest_json_file}")
        return latest_json_file

    # --- Test Setup ---
    logger.info("Running example usage for VideoGenerator.")

    config = load_config()
    if not config:
        logger.error("Failed to load config in example usage. Exiting.")
        exit()

    output_base_dir = config.get('output', {}).get('base_dir', 'output')
    audio_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('audio_subdir', 'audio'))
    image_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('images_subdir', 'images'))
    video_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('videos_subdir', 'videos')) # For saving test video

    latest_data_file = find_latest_json_data(output_base_dir)
    if not latest_data_file:
        logger.error("No JSON data file found. Cannot run example.")
        exit()

    try:
        with open(latest_data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {latest_data_file}: {e}")
        exit()

    # Get the first post for testing
    posts = []
    if isinstance(data, list):
        posts = data
    elif isinstance(data, dict) and "posts" in data and isinstance(data["posts"], list):
        posts = data["posts"]

    if not posts:
        logger.error("No post data found in JSON file. Cannot run example.")
        exit()

    test_post = posts[0]
    post_id = test_post.get("id")
    post_index = 0 # Assuming the first post has index 0 in the context of image naming

    if not post_id:
        logger.error("First post in JSON does not have an ID. Cannot run example.")
        exit()

    logger.info(f"Using post ID {post_id} for video generation example.")

    # --- Find and Concatenate Audio Files ---
    post_audio_output_dir = os.path.join(audio_base_dir, post_id)
    logger.info(f"Searching for audio files in: {post_audio_output_dir}")

    audio_files_in_post_dir = glob.glob(os.path.join(post_audio_output_dir, "*.mp3"))

    if not audio_files_in_post_dir:
        logger.error(f"No MP3 audio files found in {post_audio_output_dir}. Cannot generate video.")
        exit()

    # Sort audio files based on the defined logic (title, body, comments by number)
    def sort_audio_files(filepath):
        filename = os.path.basename(filepath)
        # Extract identifier by splitting, consistent with mapping logic
        parts = filename.split('_', 1)
        if len(parts) > 1 and parts[1].endswith('.mp3'):
            identifier = parts[1][:-4]
        else:
            # If splitting fails or not .mp3, assign a low priority sort key
            logger.warning(f"Audio filename '{filename}' did not match expected format for splitting/sorting. Assigning low priority.")
            return (999, 999) # Assign a high tuple value to put it last

        # Assign sort key based on identifier
        if identifier.startswith('title_'):
            # Title comes first
            return (0, 0)
        elif identifier.startswith('body_'):
            # Body comes second
            return (1, 0)
        elif identifier.startswith('comment'):
            # Comments come after body, sorted by comment number and part
            comment_match = re.match(r'comment(\d+)(_part_(\d+))?', identifier)
            if comment_match:
                comment_number = int(comment_match.group(1)) # 1-based number from audio identifier
                part_num = int(comment_match.group(3)) if comment_match.group(3) else 0 # Part number, default to 0
                # Sort key: (2 + comment_number, part_num) to come after title (0) and body (1)
                return (2 + comment_number, part_num)
            else:
                # If comment pattern matches but number/part extraction fails, assign medium-low priority
                logger.warning(f"Audio identifier '{identifier}' matched comment pattern but could not extract number/part for sorting. Assigning medium-low priority.")
                return (900, 0)
        else:
            # Any other identifier gets low priority
            logger.warning(f"Audio identifier '{identifier}' did not match known patterns for sorting. Assigning low priority.")
            return (999, 999)

    sorted_audio_paths = sorted(audio_files_in_post_dir, key=sort_audio_files)
    logger.info(f"Found and sorted audio files: {[os.path.basename(f) for f in sorted_audio_paths]}")
    logger.info(f"Sorted by key function: {[(os.path.basename(f), sort_audio_files(f)) for f in sorted_audio_paths]}") # Add logging for sort keys

    # Load and concatenate audio clips
    audio_clips = []
    # Get speed factor from config
    audio_speed_factor = config.get('content', {}).get('tts', {}).get('speed_factor', 1.0)
    logger.debug(f"Using audio speed factor: {audio_speed_factor}") # Log the speed factor

    for audio_path in sorted_audio_paths:
        try:
            clip = AudioFileClip(audio_path)
            # Apply speed factor if not 1.0
            if audio_speed_factor != 1.0:
                logger.debug(f"Applying speed factor {audio_speed_factor} to {os.path.basename(audio_path)}") # Log applying speed factor
                clip = clip.fx(vfx.speedx, factor=audio_speed_factor)
            audio_clips.append(clip)
        except Exception as e:
            logger.error(f"Error loading or processing audio clip {audio_path}: {e}. Skipping.") # Updated log message

    if not audio_clips:
        logger.error("No valid audio clips loaded. Cannot generate video.")
        exit()

    final_audio_clip = concatenate_audioclips(audio_clips)
    logger.info(f"Concatenated audio clip with total duration: {final_audio_clip.duration:.2f}s")

    # --- Find Images and Prepare Image Duration List ---
    json_filename_base = os.path.splitext(os.path.basename(latest_data_file))[0]
    post_image_dir = os.path.join(image_base_dir, json_filename_base)
    logger.info(f"Searching for image files in: {post_image_dir}")

    image_files_pattern = os.path.join(post_image_dir, f'post_{post_index}_*.png')
    image_files_for_post = glob.glob(image_files_pattern)

    if not image_files_for_post:
        logger.error(f"No image files found matching pattern {image_files_pattern}. Cannot generate video.")
        exit()

    # Create a map from image identifier to file path for easy lookup
    image_path_map = {}
    main_post_image_path = None
    comment_image_paths = {} # Map comment index (0-based) to path
    body_image_path = None

    for img_path in image_files_for_post:
        filename = os.path.basename(img_path)
        match = re.match(r'post_\d+_(.*)\.png$', filename)
        if match:
            identifier = match.group(1)
            image_path_map[identifier] = img_path

            if identifier == post_id:
                main_post_image_path = img_path
                logger.debug(f"Identified main post image: {filename}")
            elif identifier.startswith('comment_'):
                comment_match = re.match(r'comment_(\d+)(_part_\d+)?', identifier)
                if comment_match:
                    comment_index = int(comment_match.group(1))
                    comment_image_paths[comment_index] = img_path
                    logger.debug(f"Identified comment image for index {comment_index}: {filename}")
            elif identifier.startswith('body_'):
                body_image_path = img_path # Assuming one body image
                logger.debug(f"Identified body image: {filename}")

    if not main_post_image_path:
        logger.error(f"Could not find main post image (ending with {post_id}). Cannot generate video.")
        exit()

    # Build a map from identifier (from audio filename) to its duration
    audio_file_duration_map = {}
    logger.debug("Building audio file duration map...") # Log start of map building
    for audio_path in sorted_audio_paths:
        filename = os.path.basename(audio_path)
        logger.debug(f"Processing audio file for map: {filename}") # Log audio file being processed
        logger.debug(f"Raw filename string: {repr(filename)}") # Add logging for raw filename string

        # Extract identifier by splitting instead of regex
        parts = filename.split('_', 1) # Split only on the first underscore
        if len(parts) > 1:
            # The part after the first underscore is the identifier + .mp3
            identifier_with_ext = parts[1]
            # Remove the .mp3 extension
            if identifier_with_ext.endswith('.mp3'):
                identifier = identifier_with_ext[:-4]
                logger.debug(f"Split filename. Extracted audio identifier: {identifier}") # Log extracted identifier

                try:
                    clip = AudioFileClip(audio_path)
                    audio_file_duration_map[identifier] = clip.duration
                    logger.debug(f"Added {identifier}: {clip.duration:.2f}s to audio_file_duration_map") # Log successful addition to map
                except Exception as e:
                    logger.error(f"Error loading audio clip {audio_path} for duration map: {e}")
            else:
                logger.warning(f"Audio filename '{filename}' does not end with .mp3. Skipping map addition.") # Warn if not .mp3
        else: # Log if splitting by '_' failed (shouldn't happen with expected format)
            logger.warning(f"Audio filename '{filename}' did not contain an underscore. Cannot extract identifier. Skipping map addition.")

    logger.debug(f"Finished building audio file duration map. Map: {audio_file_duration_map}") # Log final map

    # Now map sorted images to durations using the identifier
    # The logic below will use the audio_file_duration_map, which should now be correctly populated.
    # Ensure comment index mapping is correct (image 0-based -> audio 1-based).
    # This was handled in the previous major edit, but I'll double-check.

    # Create image_duration_list by mapping audio segments to images
    image_duration_list = []

    logger.debug("Mapping audio segments to images and their durations...")
    for audio_path in sorted_audio_paths:
        filename = os.path.basename(audio_path)
        # Use splitting to get the audio identifier, consistent with map building
        parts = filename.split('_', 1)
        if len(parts) > 1 and parts[1].endswith('.mp3'):
            audio_identifier = parts[1][:-4]
        else:
            logger.warning(f"Audio filename '{filename}' did not match expected format for splitting. Skipping mapping for this file.")
            continue # Skip this audio file if identifier cannot be extracted

        current_image_path = None
        audio_duration = audio_file_duration_map.get(audio_identifier) # Get duration from the map

        if audio_duration is None:
            logger.warning(f"Audio identifier '{audio_identifier}' extracted from '{filename}' not found in audio_file_duration_map. Skipping mapping for this file.")
            continue # Skip if duration not found in map

        logger.debug(f"Processing audio segment {filename} with identifier {audio_identifier} and duration {audio_duration:.2f}s")

        # Determine which image to use based on audio identifier
        if audio_identifier.startswith('title_') or audio_identifier.startswith('body_'):
            # Use the main post image for title and body audio
            current_image_path = main_post_image_path
            logger.debug(f"Mapping audio {audio_identifier} to main post image {os.path.basename(main_post_image_path)}")

        elif audio_identifier.startswith('comment'):
            comment_audio_match = re.match(r'comment(\d+)(_part_\d+)?', audio_identifier)
            if comment_audio_match:
                comment_number = int(comment_audio_match.group(1)) # 1-based number from audio
                comment_index = comment_number - 1 # Convert to 0-based index for image map
                if comment_index in comment_image_paths:
                    current_image_path = comment_image_paths[comment_index]
                    logger.debug(f"Mapping audio {audio_identifier} (1-based comment {comment_number}) to comment image for index {comment_index} (0-based) ({os.path.basename(current_image_path)})") # Added clarity
                else:
                    logger.warning(f"No comment image found for audio identifier {audio_identifier} (expected 0-based index {comment_index}).") # Added clarity
            else:
                logger.warning(f"Audio identifier {audio_identifier} matched comment pattern but could not extract comment number.")

        if current_image_path:
            image_duration_list.append((current_image_path, audio_duration))
            logger.debug(f"Added mapping: {os.path.basename(current_image_path)} for {audio_duration:.2f}s")
        else:
            logger.warning(f"Could not find a corresponding image for audio segment {audio_identifier} ({filename}). This segment will not have an image.")

    if not image_duration_list:
        logger.error("No images could be mapped to audio durations. Cannot generate video.")
        exit()

    # The image_duration_list is now ready to be used by video_gen.generate_video
    # The sorting of images based on filename is no longer strictly necessary for building
    # the image_duration_list this way, as we iterate based on sorted audio.
    # However, the sorting function might still be useful if needed elsewhere or for verification.

    # --- Generate Video ---
    # Ensure video output directory exists
    os.makedirs(video_base_dir, exist_ok=True)
    test_video_filename = f'{post_id}_test_shorts' # Use post_id for test video name

    video_gen = VideoGenerator(output_dir=video_base_dir)

    # Call generate_video with the prepared lists/clips
    generated_video_path = video_gen.generate_video(image_duration_list, final_audio_clip, test_video_filename)

    if generated_video_path:
        logger.info(f"Video generation example successful: {generated_video_path}")
    else:
        logger.error("Video generation example failed.")

    print("\nVideo generation process completed.")
    # Note: Temporary image files (if any were created during image generation test runs) are NOT cleaned up here
    # as we are now using images from output/images. The cleanup logic in ContentImageGenerator's
    # example usage or a separate cleanup script should handle that if needed. 