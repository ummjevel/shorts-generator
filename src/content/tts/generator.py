# src/content/tts/generator.py

import os
from loguru import logger
import yaml
# Import potential TTS libraries - we will select one based on config
from gtts import gTTS # Import gTTS
# import pyttsx3

# Import the ContentImageGenerator to access the static _remove_urls method
from src.content.generator import ContentImageGenerator # Assuming src.content is in sys.path

class TTSGenerator:
    """Text-to-Speech 생성 클래스"""
    def __init__(self, config_path="config/config.yaml"):
        """TTSGenerator 초기화"""
        self.config = self._load_config(config_path)
        self.tts_settings = self.config.get('content', {}).get('tts', {})
        self.engine = self.tts_settings.get('engine', 'gtts') # Default to gTTS
        self.language = self.tts_settings.get('language', 'en')
        self.slow = self.tts_settings.get('slow', False)
        
        self._tts_engine = None
        logger.info(f"TTSGenerator initialized with engine: {self.engine}")
        
        # Initialize the chosen TTS engine
        try:
            if self.engine == 'gtts':
                # gTTS does not require explicit initialization here
                logger.info("gTTS engine selected.")
            elif self.engine == 'pyttsx3':
                # pyttsx3 requires initialization
                # import pyttsx3 # Import here to avoid dependency if not used
                # self._tts_engine = pyttsx3.init()
                # # pyttsx3 settings can be configured here if needed
                # # self._tts_engine.setProperty('rate', 150)
                # # self._tts_engine.setProperty('volume', 1)
                logger.warning("pyttsx3 engine selected but not fully implemented yet.")
                pass # Placeholder
            else:
                logger.error(f"Unsupported TTS engine specified in config: {self.engine}")
                self.engine = None # Mark engine as invalid

        except Exception as e:
            logger.error(f"Error initializing TTS engine {self.engine}: {e}")
            self.engine = None

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

    def generate_audio(self, text: str, output_filepath: str):
        """
        주어진 텍스트를 음성으로 변환하여 파일로 저장
        URL을 제거한 후 TTS를 수행합니다.
        """
        if not self.engine:
            logger.error("TTS engine is not initialized or supported. Cannot generate audio.")
            return False

        # --- Apply URL Removal ---
        cleaned_text = ContentImageGenerator._remove_urls(text)
        logger.info(f"Original text (first 50 chars): \'{text[:50]}...'")
        logger.info(f"Cleaned text (first 50 chars): \'{cleaned_text[:50]}...' to {output_filepath}")
        
        # Use the cleaned_text for TTS generation
        text_to_synthesize = cleaned_text
        
        # Skip audio generation if cleaned text is empty or very short (e.g., only punctuation)
        if not text_to_synthesize or len(text_to_synthesize.strip()) < 2: # Check length after stripping
             logger.warning(f"Cleaned text is empty or too short for audio generation: \'{text_to_synthesize}'. Skipping audio generation for {output_filepath}.")
             # Optionally, create a silent file or return a specific status
             return False # Indicate failure or skipped


        try:
            output_dir = os.path.dirname(output_filepath)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                logger.debug(f"Created output directory: {output_dir}")

            if self.engine == 'gtts':
                # gTTS generates audio directly to a file or BytesIO object
                # from gtts import gTTS # Import here to avoid dependency if not used
                tts = gTTS(text=text_to_synthesize, lang=self.language, slow=self.slow)
                tts.save(output_filepath)
                logger.info(f"gTTS audio saved to {output_filepath}")
                # logger.warning("gTTS generation logic not fully implemented yet.")
                # pass # Placeholder

            elif self.engine == 'pyttsx3':
                # pyttsx3 uses engine.say() and engine.runAndWait()
                # if self._tts_engine:
                #     self._tts_engine.save_to_file(text_to_synthesize, output_filepath)
                #     self._tts_engine.runAndWait()
                #     logger.info(f"pyttsx3 audio saved to {output_filepath}")
                logger.warning("pyttsx3 generation logic not fully implemented yet.")
                pass # Placeholder

            # logger.info(f"Audio generation placeholder completed for {output_filepath}") # Remove placeholder log
            return True # Return True on success

        except Exception as e:
            logger.error(f"Error during audio generation with {self.engine}: {e}")
            return False

# Example usage (in a test script or main workflow)
# if __name__ == "__main__":
#     # Example of how to use the class
#     generator = TTSGenerator(config_path="config/config.yaml")
#     sample_text = "안녕하세요! Shorts 자동 생성 에이전트입니다."
#     output_file = "output/audio/sample_audio.mp3"
#     success = generator.generate_audio(sample_text, output_file)
#     if success:
#         print(f"Audio generation requested for {sample_text[:20]}... to {output_file}")
#     else:
#         print("Audio generation failed.") 