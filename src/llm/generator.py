import os
from typing import Dict, Any
# Assuming potential libraries for LLM interaction (e.g., transformers, torch)
import torch
from transformers import pipeline, set_seed
from loguru import logger
import yaml # For reading config
import re # Import regex module

class ShortsContentPlanner:
    def __init__(self, config_path="config/config.yaml"):
        """Shorts 콘텐츠 기획자 초기화"""
        self.config = self._load_config(config_path)
        self.llm_settings = self.config.get('llm', {})
        # Use a smaller, commonly available text generation model as a default
        self.model_name = self.llm_settings.get('model_name', 'distilgpt2') 
        # Get max_tokens from config, default to 30 for title, ensure it's not excessively large
        config_max_tokens = self.llm_settings.get('max_tokens', 30)
        self.max_tokens = min(config_max_tokens, 128) # Limit max_tokens to a reasonable value for a title (e.g., 128)
        self.temperature = self.llm_settings.get('temperature', 0.7)
        
        # Define the model's maximum context length (specific to facebook/opt-1.3b or similar models)
        # This might need to be adjusted if self.model_name changes significantly
        self.max_model_length = 1024 # Max context length for facebook/opt-1.3b

        self._llm_pipeline = None
        logger.info(f"Attempting to load LLM model for title generation: {self.model_name}")
        
        try:
            # Load the LLM model pipeline
            self._llm_pipeline = pipeline('text-generation', model=self.model_name, device=0 if torch.cuda.is_available() else -1) # Use GPU if available
            set_seed(42) # for reproducibility
            logger.info(f"Successfully loaded LLM model for title generation: {self.model_name}")
        except Exception as e:
            logger.error(f"Error loading LLM model {self.model_name} for title generation: {e}")
            logger.error("LLM model loading failed. Title planning will use a placeholder or fail.")
            self._llm_pipeline = None # Ensure pipeline is None if loading fails

    def _load_config(self, config_path):
        """설정 파일 로드"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Config loaded from {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Config file not found at {config_path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {e}")
            return {}

    def plan_content(self, post_data: Dict[str, Any]) -> Dict[str, str]:
        """주어진 게시물 데이터를 바탕으로 Shorts 제목만 기획"""
        post_id = post_data.get('id', 'unknown_post')
        logger.info(f"Planning title for post: {post_id}")

        title = post_data.get('title', '').strip() # Get and strip title
        body = post_data.get('selftext', '').strip()
        comments = post_data.get('comments', []) # Keep comments available internally if needed later
        
        # Function to remove URLs from text (Still needed if we ever re-introduce comments)
        def remove_urls(text):
            # Simple regex to find URLs (can be expanded if needed)
            url_pattern = re.compile(r'https?://\S+|www\.\S+')
            return url_pattern.sub('', text).strip()

        # Construct a prompt for the LLM focused on title generation
        # Limit body length to prevent exceeding max context length
        max_body_length = 400 # Hardcoded limit for now
        truncated_body = body
        if len(body) > max_body_length:
            truncated_body = body[:max_body_length].rsplit(' ', 1)[0] + '...' # Truncate and end at last full word
            logger.debug(f"Truncated post body from {len(body)} to {len(truncated_body)} characters.")

        prompt = f"""You are a creative YouTube Shorts content creator. Your goal is to make people stop scrolling and watch the video.
I will provide you with a Reddit post title and body. Your task is to generate a HYPER-ENGAGING and VIRAL-WORTHY YouTube Shorts video title based on this content.

Reddit Post Title: {title if title else 'N/A'}

Reddit Post Body: {truncated_body if truncated_body else 'N/A'}

"""
        
        prompt += f"""

Please generate the YouTube Shorts title:
"""
        
        logger.debug(f"LLM Prompt for post {post_id} (Title Only):\n{prompt[:500]}...") # Log first 500 chars of prompt

        # --- Call the actual LLM API ---
        raw_generated_text = "LLM model not available or failed to generate.\nYouTube Title: Generation Error"
        if self._llm_pipeline:
            try:
                # Calculate max_length, ensuring it doesn't exceed the model's max context length
                # Also ensure it's at least the prompt length + a few tokens for the tag
                min_response_length = 20 # Minimum expected output length for title text
                calculated_max_length = len(prompt) + self.max_tokens
                
                # Ensure calculated_max_length doesn't exceed the model's max context length
                # And that it's at least long enough to potentially contain the prompt + minimal response
                safe_max_length = max(len(prompt) + min_response_length, min(calculated_max_length, self.max_model_length))

                logger.debug(f"Using safe_max_length: {safe_max_length} (Prompt length: {len(prompt)}, max_tokens: {self.max_tokens}, Model max: {self.max_model_length})")

                response = self._llm_pipeline(
                    prompt,
                    max_length=safe_max_length, 
                    num_return_sequences=1,
                    temperature=self.temperature,
                    pad_token_id=self._llm_pipeline.tokenizer.eos_token_id, 
                    return_full_text=True,
                    truncation=True # Explicitly allow truncation if prompt is too long
                )
                # The pipeline with return_full_text=True returns the prompt + generated text
                raw_generated_text = response[0]['generated_text']
                logger.debug(f"LLM Raw Generated Response for post {post_id}:\n{raw_generated_text}")

            except Exception as e:
                logger.error(f"Error during LLM text generation for post {post_id}: {e}")
                # Keep the default error message in raw_generated_text
        else:
             logger.warning(f"LLM pipeline not loaded for post {post_id}. Using default error response.")

        # --- End LLM API Call ---

        # Parse the generated text to extract title
        youtube_title = "Generated Title Placeholder"
        youtube_description = ""

        # More robust parsing: Check if the output starts with the prompt before slicing
        generated_part = raw_generated_text
        if raw_generated_text.startswith(prompt):
             # Exclude the prompt part to get only the newly generated text
             generated_part = raw_generated_text[len(prompt):].strip()
             logger.debug(f"Extracted generated part for post {post_id}:\n{generated_part}")
        else:
             logger.warning(f"LLM output for post {post_id} does not start with the prompt. Parsing the full output. Raw response:\n{raw_generated_text}")
             # If output doesn't start with prompt, maybe the model didn't follow instructions
             # or returned something unexpected. Try parsing the whole thing.
             # Or, if the model *didn't* return the full text, generated_part is already correct.
             # Let's proceed with parsing generated_part which might be the full output or sliced.

        try:
            lines = generated_part.strip().split('\n')
            # Find the first non-empty line as the title
            first_line = next((line for line in lines if line.strip()), None)

            if first_line:
                 youtube_title = first_line.strip()
                 logger.info(f"Using first non-empty line as title for post {post_id}: '{youtube_title}'")
            elif "Generation Error" in raw_generated_text:
                 # If generation failed, the raw text might contain the error message
                 youtube_title = "Generation Error"
            else:
                 logger.warning(f"Could not find any non-empty line in LLM response for post {post_id}. Generated part:\n{generated_part}")
                 youtube_title = "Could Not Generate Title"

            # Description will be empty string as we are only generating title
            youtube_description = ""


        except Exception as e:
            logger.error(f"Error parsing LLM response for post {post_id}: {e}. Generated part was:\n{generated_part}")
            # Fallback to using a default error message for title
            youtube_title = "Parsing Error Title"
            youtube_description = ""

        logger.info(f"Planned content for post {post_id}: Title='{youtube_title}'") # Log only title

        return {
            "youtube_title": youtube_title,
            "youtube_description": youtube_description # Description is empty
        }

# Example usage (in test_generator.py or __main__ block if desired)
# if __name__ == "__main__":
#     # Need to load sample post data from a JSON file
#     sample_post_data = { # Replace with actual loaded data
#         "id": "sample_post_123",
#         "title": "What's the most unexpected thing that happened to you today?",
#         "selftext": "Just a regular Monday morning and then suddenly... a wild squirrel brought me a nut!",
#         "comments": [
#             {"author": "SquirrelFan", "body": "Wow, lucky you! Must be a sign."},
#             {"author": "ConfusedHuman", "body": "Did you keep the nut? What did you do?"}
#         ]
#     }
    
#     planner = ShortsContentPlanner()
#     shorts_plan = planner.plan_content(sample_post_data)
#     print(shorts_plan) 