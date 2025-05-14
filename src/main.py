import os
import glob
import json
import yaml
from loguru import logger

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

    # --- Step 2: Process Latest Collected Data (Images and Audio) ---
    logger.info("Processing latest collected data...")
    # Find the latest JSON data file in output directory (based on previous tests)
    output_json_files = glob.glob(os.path.join(output_base_dir, "*.json"))
    if not output_json_files:
        logger.error(f"No Reddit data JSON files found in {output_base_dir}. Exiting.")
        return

    latest_json_file = max(output_json_files, key=os.path.getctime)
    logger.info(f"Using latest data file: {latest_json_file}")
    json_filename_base = os.path.splitext(os.path.basename(latest_json_file))[0]
    current_image_output_dir = os.path.join(image_base_dir, json_filename_base)
    os.makedirs(current_image_output_dir, exist_ok=True)
    logger.info(f"Images for this run will be saved to: {current_image_output_dir}")

    # Load the collected data
    try:
        with open(latest_json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {latest_json_file}: {e}")
        return
    
    # Check if data is a list of posts or a dictionary containing posts
    if isinstance(data, list):
        posts = data
    elif isinstance(data, dict) and "posts" in data and isinstance(data["posts"], list):
        posts = data["posts"]
    else:
        logger.error(f"Unexpected data format in {latest_json_file}. Expected a list or a dictionary with a 'posts' key containing a list. Exiting.")
        return

    if not posts:
        logger.warning(f"No post data found in {latest_json_file}. Exiting.")
        return

    # Initialize generators
    # Image Generator - pass the specific output subdirectory for this run
    image_generator = ContentImageGenerator(output_dir=current_image_output_dir)
    # TTS Generator - pass config or rely on it loading internally
    tts_generator = TTSGenerator(config_path="config/config.yaml") # Assuming TTSGenerator handles its output dir internally or based on output_filepath

    # Iterate through each post in the data to generate images and audio
    processed_posts_data = [] # To store data with paths to generated files
    for post_index, post_data in enumerate(posts):
        post_id = post_data.get("id")
        if not post_id:
            logger.warning(f"Skipping post at index {post_index} with no id: {post_data.get('title', 'N/A')}")
            continue

        logger.info(f"\nProcessing Post Index: {post_index}, Post ID: {post_id}")

        # Define the specific audio output directory for this post
        post_audio_output_dir = os.path.join(audio_base_dir, post_id)
        os.makedirs(post_audio_output_dir, exist_ok=True)

        # --- Generate Audio for the Post ---
        # Extract text for TTS (title, body, comments) - URL removal is handled inside TTSGenerator
        text_for_tts = post_data.get("title", "") + "\n\n" + post_data.get("body", "")
        # Sort comments by score to process popular ones first for TTS/images
        sorted_comments = sorted(post_data.get('comments', []), key=lambda c: c.get('score', 0), reverse=True)
        # Limit comments to top N (e.g., 5, based on config or previous logic)
        max_comments_per_post = config.get('reddit', {}).get('max_comments_per_post', 5)
        comments_to_process = sorted_comments[:max_comments_per_post]

        audio_segment_map = {} # Map segment identifier (e.g., 'title_1', 'comment1_1') to audio filepath

        # Generate audio for title
        title_text = post_data.get("title", "")
        if title_text:
             # Save audio to the post-specific directory
             title_audio_filepath = os.path.join(post_audio_output_dir, f"title_1.mp3") # Use mp3 as default output format
             if tts_generator.generate_audio(title_text, title_audio_filepath):
                 audio_segment_map['title_1'] = title_audio_filepath

        # Generate audio for body
        body_text = post_data.get("body", "")
        if body_text:
             # Save audio to the post-specific directory
             body_audio_filepath = os.path.join(post_audio_output_dir, f"body_1.mp3") # Use mp3
             if tts_generator.generate_audio(body_text, body_audio_filepath):
                 audio_segment_map['body_1'] = body_audio_filepath

        # Generate audio for comments
        for c_idx, comment in enumerate(comments_to_process):
            comment_author = comment.get('author', '') or '[Deleted]'
            comment_body = comment.get('body', '') or ''
            # Combine author and body for TTS
            comment_text = f"{comment_author}: {comment_body}"
            # Assuming comment text is not split into parts for audio generation in TTS module
            # Save audio to the post-specific directory
            comment_audio_filepath = os.path.join(post_audio_output_dir, f"comment{c_idx+1}_1.mp3") # Use 1-based index for comment audio file naming
            if tts_generator.generate_audio(comment_text, comment_audio_filepath):
                 audio_segment_map[f'comment{c_idx+1}_1'] = comment_audio_filepath

        # --- Generate Images for the Post ---
        # The ContentImageGenerator's generate_from_json method is designed to process the whole file.
        # We need to adapt it or call post_to_images directly here for a single post.
        # Let's assume generate_from_json can be adapted or we use post_to_images.
        # The previous structure in generate_from_json for ImageGenerator processed all posts.
        # Need to clarify if image generator should process per-post here or process the whole file once.
        # Given the video generation needs images per post, processing per-post here makes sense.
        # The ContentImageGenerator already handles writing to the correct subdirectory.
        image_generator.current_post_index = post_index # Ensure index is set for filename
        post_image_files = image_generator.post_to_images(post_data) # Generate images for this single post
        logger.info(f"Generated {len(post_image_files)} image files for post {post_id}.")

        # --- Prepare Data for Video Generation ---
        # We need a list of (image_filepath, duration) tuples
        # Durations are derived from the audio segments
        image_duration_list = []

        # Sort the audio segments by key (e.g., 'title_1', 'body_1', 'comment1_1', ...) - Use filepaths from the post-specific directory
        # This sorting logic should match the order in which images are intended to be displayed.
        # The sorting key logic developed in video/generator.py's example usage can be reused or adapted.
        def sort_audio_segments(item):
            identifier, filepath = item # item is a tuple (identifier, filepath)
            filename = os.path.basename(filepath) # Get just the filename for sorting logic
            
            # Use a similar sorting logic as in video/generator.py's example usage's sort_audio_files
            # This assumes the identifier derived from filename matches the logic
            if filename.startswith('title_'): return 0
            if filename.startswith('body_'): return 1
            comment_match = re.match(r'comment(\d+)_(\d+)', filename) # Match comment[number]_[part] pattern
            if comment_match:
                 # Sort by comment number then part number
                 return (2 + int(comment_match.group(1)), int(comment_match.group(2))) # comments come after title and body
            
            # Handle simple comment names like comment[number].mp3 if they exist (less likely with current TTS output)
            comment_simple_match = re.match(r'comment(\d+)', filename)
            if comment_simple_match:
                 return (2 + int(comment_simple_match.group(1)), 0) # Assume part 0 if no part number

            return (999, 0) # Fallback for unexpected identifiers
            
        # Sort the audio segments map items
        sorted_audio_segments_items = sorted(audio_segment_map.items(), key=sort_audio_segments)

        # Load sorted audio clips, apply speed factor, and get durations
        processed_audio_clips = [] # List of (identifier, speed_adjusted_AudioClip) tuples
        image_duration_list = [] # List of (image_filepath, duration) tuples derived from adjusted audio

        audio_speed_factor = config.get('content', {}).get('tts', {}).get('speed_factor', 1.0)
        logger.info(f"Applying audio speed factor: {audio_speed_factor}")

        # Match images to audio segments to pre-build mapping for durations
        image_identifier_map = {} # Map identifier (e.g., 'title_1', 'comment1_1') to image filepath
        for img_path in post_image_files:
             filename = os.path.basename(img_path)
             # Extract the part after post_[index]_[post_id]_ and before .png
             # Ensure this regex matches the image naming convention from ContentImageGenerator
             match = re.match(f'post_{post_index}_{re.escape(post_id)}_(.*)\\.png', filename)
             if match:
                 identifier = match.group(1) # The extracted part IS the identifier
                 image_identifier_map[identifier] = img_path
             else:
                  logger.warning(f"Image filename {filename} did not match expected pattern for post {post_id}. Cannot map to audio segment.")

        for identifier, audio_path in sorted_audio_segments_items:
             try:
                 clip = AudioFileClip(audio_path)
                 logger.debug(f"Loaded audio clip for {identifier} with original duration {clip.duration:.2f}s from {audio_path}")

                 # Apply speed factor to the individual clip
                 if audio_speed_factor != 1.0:
                     try:
                         speed_adjusted_clip = clip.fx(vfx.speedx, factor=audio_speed_factor)
                         logger.debug(f"Applied speed factor {audio_speed_factor} to {identifier}. New duration: {speed_adjusted_clip.duration:.2f}s")
                     except Exception as e:
                         logger.error(f"Error applying speedx effect to audio segment {identifier}: {e}. Using original speed/duration.")
                         speed_adjusted_clip = clip # Fallback to original clip if error
                 else:
                      speed_adjusted_clip = clip # No speed adjustment needed

                 processed_audio_clips.append((identifier, speed_adjusted_clip)) # Store the adjusted clip

                 # Get the duration from the speed-adjusted clip
                 adjusted_duration = speed_adjusted_clip.duration

                 # Find the corresponding image and add to image_duration_list
                 if identifier in image_identifier_map:
                     image_path = image_identifier_map[identifier]
                     image_duration_list.append((image_path, adjusted_duration))
                     logger.debug(f"Mapping image {os.path.basename(image_path)} to audio segment {identifier} with ADJUSTED duration {adjusted_duration:.2f}s")
                 else:
                     logger.warning(f"No image found for audio segment identifier {identifier} for post {post_id}. Cannot include this segment in video.")

             except Exception as e:
                 logger.error(f"Error loading or processing audio clip for identifier {identifier} from {audio_path}: {e}. Skipping segment.")

        if not processed_audio_clips or not image_duration_list:
             logger.warning(f"No processed audio clips or image durations for post ID {post_id}. Cannot generate video.")
             continue # Skip video generation if no audio or image mapping

        # Concatenate the speed-adjusted audio clips
        final_audio_clip = concatenate_audioclips([clip for identifier, clip in processed_audio_clips])
        logger.info(f"Concatenated FINAL audio clip for post {post_id} with total duration: {final_audio_clip.duration:.2f}s")

        # Verify total durations match (should be very close)
        total_image_duration_sum = sum([item[1] for item in image_duration_list])
        if abs(total_image_duration_sum - final_audio_clip.duration) > 0.1: # Allow small floating point differences
            logger.warning(f"Total image duration ({total_image_duration_sum:.2f}s) does not match final audio duration ({final_audio_clip.duration:.2f}s) for post {post_id}. Sync issues may occur.")
        else:
            logger.info(f"Total image duration ({total_image_duration_sum:.2f}s) matches final audio duration ({final_audio_clip.duration:.2f}s) for post {post_id}.")

        # --- Step 4: Generate Video ---
        logger.info(f"Generating video for post ID {post_id}...")
        video_filename = post_id # Use post_id as the video filename
        video_generator = VideoGenerator(output_dir=video_base_dir) # Ensure VideoGenerator saves to the correct output dir
        generated_video_path = video_generator.generate_video(image_duration_list, final_audio_clip, video_filename)

        if generated_video_path:
            logger.info(f"Successfully generated video for post {post_id} at: {generated_video_path}")
        else:
            logger.error(f"Failed to generate video for post {post_id}.")

    logger.info("Shorts Agent Main Script Finished.")

if __name__ == "__main__":
    main() 