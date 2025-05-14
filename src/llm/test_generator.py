import os
import json
# from ..llm.generator import ShortsContentPlanner
from generator import ShortsContentPlanner
from loguru import logger

# Assuming sample JSON files are in the output directory
OUTPUT_DIR = 'output'

def main():
    # Set up basic logging if loguru is available (for testing)
    try:
        from loguru import logger
        logger.info("LLM Test Generator script started.")
    except ImportError:
        print("Loguru not installed. Running without detailed logging.")
        logger = None

    # Find a sample JSON file to use
    json_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')]

    if not json_files:
        if logger:
            logger.warning(f"No .json files found in {OUTPUT_DIR}. Please run data collection first.")
        print(f"No .json files found in {OUTPUT_DIR}. Please run data collection first.")
        return

    # Use the first found JSON file as a sample (assuming one file per subreddit)
    sample_json_path = os.path.join(OUTPUT_DIR, json_files[0])

    try:
        # Read the entire JSON file
        with open(sample_json_path, 'r', encoding='utf-8') as f:
            posts_data = json.load(f)

        if not posts_data or not isinstance(posts_data, list) or not posts_data[0]: # Check for empty list or non-dict first item
             if logger: # Assuming logger is available
                 logger.error(f"Sample JSON file {sample_json_path} is empty or does not contain a list of post dictionaries.")
             print(f"Error: Sample JSON file {sample_json_path} is empty or does not contain a list of post dictionaries.")
             return

        if logger:
            logger.info(f"Loaded {len(posts_data)} posts from {sample_json_path} for planning.")
        print(f"Loaded {len(posts_data)} posts from {sample_json_path} for planning.")

        # Initialize the ShortsContentPlanner
        planner = ShortsContentPlanner(config_path="config/config.yaml")

        # Process each post in the list
        processed_count = 0
        for i, post_data in enumerate(posts_data):
            post_id = post_data.get('id', f'unknown_post_{i}')
            if logger:
                logger.info(f"Processing post {i+1}/{len(posts_data)} (ID: {post_id})...")
            print(f"Processing post {i+1}/{len(posts_data)} (ID: {post_id})...")

            try:
                # Generate YouTube Shorts title and description
                shorts_plan = planner.plan_content(post_data)

                # Add the generated fields to the current post dictionary in the list
                posts_data[i]['youtube_title'] = shorts_plan.get('youtube_title')
                posts_data[i]['youtube_description'] = shorts_plan.get('youtube_description')

                if logger:
                    logger.info(f"Generated plan for post {post_id}: Title='{shorts_plan.get('youtube_title')}', Description='{shorts_plan.get('youtube_description')}'")
                print(f"Generated plan for post {post_id}: Title='{shorts_plan.get('youtube_title')}', Description='{shorts_plan.get('youtube_description')}'")
                processed_count += 1

            except Exception as e:
                if logger:
                    logger.error(f"Error planning content for post {post_id}: {e}")
                print(f"Error planning content for post {post_id}: {e}")

        # Save the entire modified list back to the original JSON file after processing all posts
        if processed_count > 0:
            with open(sample_json_path, 'w', encoding='utf-8') as f:
                json.dump(posts_data, f, ensure_ascii=False, indent=2)

            if logger:
                logger.info(f"Saved generated plans for {processed_count} posts back to {sample_json_path}.")
            print(f"Saved generated plans for {processed_count} posts back to {sample_json_path}.")
        else:
             if logger:
                 logger.warning(f"No posts were processed from {sample_json_path}. No changes saved.")
             print(f"No posts were processed from {sample_json_path}. No changes saved.")


    except FileNotFoundError:
         if logger:
             logger.error(f"Sample JSON file not found at {sample_json_path}")
         print(f"Error: Sample JSON file not found at {sample_json_path}")
    except Exception as e:
        if logger:
            logger.error(f"An error occurred during LLM test generation and saving: {e}")
        print(f"An error occurred during LLM test generation and saving: {e}")

    if logger:
        logger.info("LLM Test Generator script finished.")
    print("LLM Test Generator script finished.")

if __name__ == "__main__":
    main() 