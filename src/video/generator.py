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
from datetime import datetime

# 기존 logger 설정을 따르거나 기본 로거 사용
try:
    from loguru import logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


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
                        # Try parsing with different formats
                        if '-' in date_str:
                            current_file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        else:
                            current_file_date = datetime.strptime(date_str, '%Y%m%d').date()
                        break # Found and parsed a date, no need to try other patterns
                    except ValueError:
                        continue # Mismatch with date format, try next pattern

            if current_file_date:
                # Update latest_date if this file is newer
                if latest_date is None or current_file_date > latest_date:
                    latest_date = current_file_date

                # Add the file to the map, creating a new list if date is encountered first time
                date_to_files_map.setdefault(current_file_date, []).append(filepath)

        # Collect all files corresponding to the latest date found
        latest_files = date_to_files_map.get(latest_date, [])

        if latest_files:
            logger.info(f"Found {len(latest_files)} file(s) with the latest date ({latest_date}):")
            for f in latest_files:
                logger.info(f"  - {os.path.basename(f)}")
            return latest_files
        else:
            logger.warning(f"No JSON data files with parsable dates found in {base_output_dir}.")
            # Fallback to using creation time if no date found in filenames with parsable date
            if output_json_files:
                logger.info("Falling back to finding the single latest file based on creation time.")
                latest_json_file_ctime = max(output_json_files, key=os.path.getctime)
                logger.info(f"Using latest data file based on creation time: {os.path.basename(latest_json_file_ctime)}")
                return [latest_json_file_ctime] # Return a list containing the single latest file
            else:
                return [] # Should not happen based on initial check, but for safety


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
        Generates a video clips from a sequence of images and an audio file.

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

    # Ensure src directory is in sys.path for imports like src.content.generator
    import sys
    import os
    # Assuming video/generator.py is in src/video/
    # Go up two directories from the current file to reach the project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    sys.path.insert(0, project_root)

    # ContentImageGenerator와 TTSGenerator는 이미지/오디오 생성을 위해 필요합니다.
    try:
        # 프로젝트 구조에 따라 import 경로를 조정해야 할 수 있습니다.
        from src.content.generator import ContentImageGenerator
        from src.content.tts.generator import TTSGenerator
    except ImportError as e:
        logger.error(f"__main__ 블록에서 ContentImageGenerator 또는 TTSGenerator 임포트 실패: {e}. src 디렉토리가 sys.path에 있는지 확인하거나 import 경로를 조정하세요.")
        exit(1) # 필수 모듈 임포트 실패 시 종료

    # 식별자별로 오디오 세그먼트 정렬 함수 정의 (예: 'title_1', 'body_1', 'comment1_1', ...)
    def sort_audio_segments(item):
        identifier, filepath = item
        filename = os.path.basename(filepath)
        if filename.startswith('title_'): return (0, 0)
        if filename.startswith('body_'): return (1, 0)
        comment_match = re.match(r'comment(\d+)_(\d+)', filename)
        if comment_match:
            return (2 + int(comment_match.group(1)), int(comment_match.group(2)))
        comment_simple_match = re.match(r'comment(\d+)', filename)
        if comment_simple_match:
            return (2 + int(comment_simple_match.group(1)), 0)
        return (999, 0)

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

    logger.info("VideoGenerator 스크립트를 직접 실행합니다.")

    config = load_config()
    if not config:
        logger.error("설정 파일 로드 실패. 종료합니다.")
        exit()

    output_base_dir = config.get('output', {}).get('base_dir', 'output')
    audio_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('audio_subdir', 'audio'))
    image_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('images_subdir', 'images'))
    video_base_dir = os.path.join(output_base_dir, config.get('output', {}).get('videos_subdir', 'videos')) # 생성된 영상을 저장할 기본 디렉토리

    # 업데이트된 find_latest_json_data 함수를 사용하여 최신 파일 목록을 가져옵니다.
    latest_data_files = find_latest_json_data(output_base_dir)
    # latest_data_files = [latest_data_files[0]]
    if not latest_data_files:
        logger.error("처리할 데이터 파일을 찾지 못했습니다. 종료합니다.")
        exit()

    total_posts_processed = 0
    total_videos_generated = 0
    # VideoGenerator 인스턴스는 각 게시물별 하위 디렉토리에 저장하도록 루프 안에서 초기화합니다.
    # video_generator_base = VideoGenerator(output_dir=video_base_dir)

    # --- 최신 데이터 파일 목록을 순회합니다 ---
    for data_filepath in latest_data_files:
        logger.info(f"\n데이터 파일 처리 중: {os.path.basename(data_filepath)}")

        # 현재 파일에서 데이터 로드
        try:
            with open(data_filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"JSON 파일 로드 오류 {data_filepath}: {e}. 이 파일을 건너뜁니다.")
            continue # 다음 파일로 이동

        posts = []
        if isinstance(data, list):
            posts = data
        elif isinstance(data, dict) and "posts" in data and isinstance(data["posts"], list):
            posts = data["posts"]
        else:
            logger.error(f"예상치 못한 데이터 형식입니다 {data_filepath}. 리스트 또는 'posts' 키를 가진 딕셔너리(리스트 포함)가 필요합니다. 이 파일을 건너뜁니다.")
            continue # 다음 파일로 이동

        if not posts:
            logger.warning(f"데이터가 없습니다 {data_filepath}. 이 파일을 건너뜁니다.")
            continue # 다음 파일로 이동

        logger.info(f"{os.path.basename(data_filepath)}에서 {len(posts)}개의 게시물을 찾았습니다.")

        # 게시물 처리를 위한 ContentImageGenerator 및 TTSGenerator 초기화
        image_generator = ContentImageGenerator(output_dir=image_base_dir) # 이미지 저장 기본 디렉토리, 게시물별 하위 디렉토리는 나중에 설정
        tts_generator = TTSGenerator(config_path="config/config.yaml")

        # --- 현재 데이터 파일 내의 각 게시물을 순회합니다 ---
        for post_index, post_data in enumerate(posts):
            post_id = post_data.get("id")
            if not post_id:
                logger.warning(f"게시물 ID가 없는 게시물 (인덱스 {post_index}, 파일 {os.path.basename(data_filepath)})을 건너뜁니다.")
                continue

            logger.info(f"\n게시물 처리 중 - 인덱스: {post_index}, ID: {post_id} (파일: {os.path.basename(data_filepath)})")
            total_posts_processed += 1

            # 이 특정 게시물에 대한 출력 디렉토리 정의
            current_post_image_output_dir = os.path.join(image_base_dir, post_id)
            post_audio_output_dir = os.path.join(audio_base_dir, post_id)
            post_video_output_dir = os.path.join(video_base_dir, post_id)

            os.makedirs(current_post_image_output_dir, exist_ok=True)
            os.makedirs(post_audio_output_dir, exist_ok=True)
            os.makedirs(post_video_output_dir, exist_ok=True)

            # 게시물 처리를 위한 ContentImageGenerator 및 TTSGenerator 인스턴스 설정 (루프 안에서)
            image_generator.output_dir = current_post_image_output_dir # 이 게시물에 대한 출력 디렉토리 설정
            image_generator.current_post_index = post_index # 파일 이름에 사용할 인덱스 설정

            # --- 게시물 이미지 생성 ---
            # 이 단일 게시물에 대한 이미지 생성 및 파일 목록 가져오기
            post_image_files = [] # Initialize to an empty list
            try:
                # image_generator 내에서 파일 이름을 생성할 때 post_index를 사용하므로 여기서 post_data를 그대로 전달합니다.
                post_image_files = image_generator.post_to_images(post_data) # post_data 안에는 'id', 'title', 'body', 'comments' 등 정보가 있습니다.
                logger.info(f"게시물 {post_id} (인덱스: {post_index})에 대해 {len(post_image_files)}개의 이미지 파일을 생성했습니다.") # post_index 로깅 추가
            except Exception as e:
                logger.error(f"ERROR: 게시물 {post_id} (인덱스: {post_index}) 이미지 생성 중 오류 발생: {e}") # post_index 로깅 추가
                # 이미지 생성 실패 시 해당 게시물 건너뛰기
                logger.warning(f"WARNING: 게시물 {post_id} (인덱스: {post_index}) 이미지 생성 실패로 영상 생성을 건너뜁니다.") # post_index 로깅 추가
                total_posts_processed -= 1 # Subtract if we incremented earlier
                continue # 다음 게시물로 이동

            if not post_image_files:
                logger.warning(f"WARNING: 게시물 {post_id} (인덱스: {post_index})에 대한 이미지 파일이 생성되지 않았습니다. 영상 생성을 건너킵니다.") # post_index 로깅 추가
                total_posts_processed -= 1 # Subtract if we incremented earlier
                continue # 다음 게시물로 이동

            # --- 게시물 오디오 생성 ---
            audio_segment_map = {} # 세그먼트 식별자와 오디오 파일 경로 매핑
            # 기존 오디오 생성 로직 재사용

            # 오디오 속도 계수 설정
            audio_speed_factor = config.get('content', {}).get('tts', {}).get('speed_factor', 1.0)
            logger.info(f"오디오 속도 계수 적용: {audio_speed_factor}")

            # 누적 영상 길이 초기화 및 목표 길이 설정
            target_video_duration_seconds = config.get('video', {}).get('max_duration_seconds', 60) # 설정에서 가져오기 (기본 60초)
            current_video_duration = 0 # 누적 영상 길이

            # 제목 오디오 생성
            title_text = post_data.get("title", "")
            if title_text:
                 title_audio_filepath = os.path.join(post_audio_output_dir, f"title_1.mp3")
                 logger.info(f"제목 오디오 생성 중...")
                 if tts_generator.generate_audio(title_text, title_audio_filepath):
                     audio_segment_map['title_1'] = title_audio_filepath
                 else:
                     logger.warning("제목 오디오 생성 실패.")

            # 본문 오디오 생성
            body_text = post_data.get("body", "")
            if body_text:
                 body_audio_filepath = os.path.join(post_audio_output_dir, f"body_1.mp3")
                 logger.info(f"본문 오디오 생성 중...")
                 if tts_generator.generate_audio(body_text, body_audio_filepath):
                     audio_segment_map['body_1'] = body_audio_filepath
                 else:
                     logger.warning("본문 오디오 생성 실패.")

            # 댓글 오디오 생성
            sorted_comments = sorted(post_data.get('comments', []), key=lambda c: c.get('score', 0), reverse=True)
            max_comments_per_post = config.get('reddit', {}).get('max_comments_per_post', 5)
            comments_to_process = sorted_comments[:max_comments_per_post]

            if comments_to_process:
                logger.info(f"상위 {len(comments_to_process)}개 댓글 오디오 생성 중...")
                
                # 제목 및 본문 오디오 길이 합산 (이미 생성된 오디오 사용)
                title_audio = AudioFileClip(audio_segment_map.get('title_1', '')) if audio_segment_map.get('title_1') and os.path.exists(audio_segment_map.get('title_1', '')) else None
                body_audio = AudioFileClip(audio_segment_map.get('body_1', '')) if audio_segment_map.get('body_1') and os.path.exists(audio_segment_map.get('body_1', '')) else None
                
                if title_audio: current_video_duration += title_audio.duration
                if body_audio: current_video_duration += body_audio.duration
                
                logger.debug(f"제목+본문 오디오 초기 길이: {current_video_duration:.2f}s")

                for c_idx, comment in enumerate(comments_to_process):
                    comment_author = comment.get('author', '') or '[Deleted]'
                    comment_body = comment.get('body', '') or ''
                    comment_text = f"{comment_author}: {comment_body}"
                    comment_audio_filepath = os.path.join(post_audio_output_dir, f"comment{c_idx+1}_1.mp3")

                    # 댓글 오디오 생성 시도
                    if tts_generator.generate_audio(comment_text, comment_audio_filepath):
                        # 생성된 댓글 오디오 파일 로드하여 길이 확인
                        try:
                            comment_audio_clip = AudioFileClip(comment_audio_filepath)
                            comment_duration = comment_audio_clip.duration
                            
                            # 총 영상 길이를 초과하는지 확인
                            if current_video_duration + comment_duration <= target_video_duration_seconds:
                                logger.info(f"댓글 {c_idx+1} 오디오 ({comment_duration:.2f}s) 포함. 누적 길이: {current_video_duration + comment_duration:.2f}s")
                                audio_segment_map[f'comment{c_idx+1}_1'] = comment_audio_filepath # 포함 확정
                                current_video_duration += comment_duration # 누적 길이 업데이트
                            else:
                                logger.info(f"댓글 {c_idx+1} 오디오 ({comment_duration:.2f}s) 포함 시 총 길이 ({current_video_duration + comment_duration:.2f}s)가 {target_video_duration_seconds}s를 초과. 이 이후 댓글은 제외.")
                                # 목표 길이 초과 시, 생성된 오디오 파일 삭제 및 이후 댓글 처리 중단
                                if os.path.exists(comment_audio_filepath):
                                    os.remove(comment_audio_filepath)
                                    logger.debug(f"초과 길이로 인해 댓글 오디오 파일 삭제됨: {comment_audio_filepath}")
                                break # 댓글 순회 중단
                                
                        except Exception as e:
                            logger.error(f"댓글 {c_idx+1} 오디오 파일 로드 또는 처리 오류: {e}. 이 댓글은 제외합니다.")
                            # 오류 발생 시 생성된 파일 삭제
                            if os.path.exists(comment_audio_filepath):
                                 os.remove(comment_audio_filepath)
                                 logger.debug(f"오류로 인해 댓글 오디오 파일 삭제됨: {comment_audio_filepath}")
                                
                    else:
                         logger.warning(f"댓글 {c_idx+1} 오디오 생성 실패. 이 댓글은 제외합니다.")

            # 댓글 오디오 처리 완료 후, 실제로 audio_segment_map에 포함된 오디오만 가지고 processed_audio_clips와 image_duration_list_final 구성
            # 이제 audio_segment_map에 최종적으로 포함된 오디오 파일들을 바탕으로
            # processed_audio_clips와 audio_clip_duration_map을 재구성합니다.
            
            # audio_segment_map의 항목을 정렬 (제목, 본문, 댓글 순서)
            final_audio_segments_items = sorted(audio_segment_map.items(), key=sort_audio_segments)

            audio_clip_duration_map = {} # Store durations by identifier
            processed_audio_clips = [] # processed audio clips list

            # 정렬된 최종 오디오 세그먼트 로드, 속도 계수 적용, 지속 시간 저장 및 리스트 추가
            for identifier, audio_path in final_audio_segments_items:
                 if os.path.exists(audio_path):
                     try:
                         clip = AudioFileClip(audio_path)
                         logger.debug(f"오디오 클립 로드 - 식별자: {identifier}, 원본 지속 시간: {clip.duration:.2f}s (파일: {audio_path})")

                         if audio_speed_factor != 1.0:
                             speed_adjusted_clip = clip.fx(vfx.speedx, factor=audio_speed_factor)
                             logger.debug(f"속도 계수 {audio_speed_factor} 적용 - 식별자: {identifier}. 새 지속 시간: {speed_adjusted_clip.duration:.2f}s")
                         else:
                             speed_adjusted_clip = clip

                         # Add the processed clip to the list
                         processed_audio_clips.append(speed_adjusted_clip)

                         # 속도 조정된 클립의 지속 시간을 오디오 클립 지속 시간 맵에 저장
                         audio_clip_duration_map[identifier] = speed_adjusted_clip.duration # Store duration by identifier

                     except Exception as e:
                         logger.error(f"오디오 클립 처리 오류 - 파일 {audio_path}, 식별자 {identifier}: {e}")
                 else:
                      logger.warning(f"오디오 파일을 찾을 수 없습니다 - 경로 {audio_path}, 식별자 {identifier}.")

            # 이미지 지속 시간 목록을 오디오 순서에 맞춰 구성
            image_duration_list_final = []
            current_images = [] # 이미지 순서 기록 (디버그용 또는 이후 활용)

            # 1. 제목 이미지 추가 (title_1 오디오에 매핑)
            title_audio_identifier = 'title_1'
            # Find the main post image (title/body combined)
            # Filename format is post_[post_idx]_[post_id].png
            # post_index는 enumerate 루프 변수 사용
            # post_id는 post_data.get("id", "unknown") 사용
            main_post_image_pattern = f"post_{post_index}_{post_id}.png" # Use the loop variable post_index
            main_post_images = [img_path for img_path in post_image_files if os.path.basename(img_path) == main_post_image_pattern]

            # For title and body, use the main post image if found
            title_matching_images = main_post_images

            logger.debug(f"오디오 세그먼트 {title_audio_identifier}에 대해 찾은 매칭 이미지: {title_matching_images}")
            if title_matching_images:
                total_audio_duration_for_segment = audio_clip_duration_map.get(title_audio_identifier, 0)
                num_matching_images = len(title_matching_images)
                duration_per_image = total_audio_duration_for_segment / num_matching_images if num_matching_images > 0 else 0
                for img_path in title_matching_images:
                    image_duration_list_final.append((img_path, duration_per_image))
                    current_images.append(img_path)
                    logger.debug(f"이미지 {os.path.basename(img_path)}를 오디오 {title_audio_identifier}에 매핑 - 초기 지속 시간: {duration_per_image:.2f}s")
            else:
                logger.warning(f"게시물 {post_id}의 오디오 세그먼트 {title_audio_identifier}에 해당하는 이미지를 찾지 못했습니다. 이 오디오 세그먼트에는 이미지가 표시되지 않습니다.")

            # 2. 본문 이미지 추가 (body_1 오디오에 매핑)
            body_audio_identifier = 'body_1'
            # For body, also use the main post image if found
            body_matching_images = main_post_images # Use the same main image as for title

            logger.debug(f"오디오 세그먼트 {body_audio_identifier}에 대해 찾은 매칭 이미지: {body_matching_images}")
            if body_matching_images:
                total_audio_duration_for_segment = audio_clip_duration_map.get(body_audio_identifier, 0)
                num_matching_images = len(body_matching_images)
                duration_per_image = total_audio_duration_for_segment / num_matching_images if num_matching_images > 0 else 0
                for img_path in body_matching_images:
                    image_duration_list_final.append((img_path, duration_per_image))
                    current_images.append(img_path)
                    logger.debug(f"이미지 {os.path.basename(img_path)}를 오디오 {body_audio_identifier}에 매핑 - 초기 지속 시간: {duration_per_image:.2f}s")
            else:
                logger.warning(f"게시물 {post_id}의 오디오 세그먼트 {body_audio_identifier}에 해당하는 이미지를 찾지 못했습니다. 이 오디오 세그먼트에는 이미지가 표시되지 않습니다.")

            # 3. 댓글 이미지 추가 (commentX_Y 오디오에 매핑)
            # 오디오 세그먼트 목록에서 title_1, body_1을 제외하고 댓글 오디오만 처리
            comment_audio_segments = [item for item in final_audio_segments_items if item[0].startswith('comment')]

            for identifier, _ in comment_audio_segments:
                 # 이 오디오 세그먼트에 해당하는 이미지 찾기
                 comment_match = re.match(r'comment(\d+)_(\d+)', identifier)
                 matching_images = [] # Reset matching_images for each comment segment
                 if comment_match:
                      comment_display_idx = int(comment_match.group(1))
                      audio_part_idx = int(comment_match.group(2)) # Part index from audio identifier (usually 1)

                      # Find all image parts for this comment
                      # Search for filenames containing `comment_{comment_display_idx-1}_part_` and ending with `.png`
                      # Note: Image generator uses 0-based index for comment, audio uses 1-based display index
                      comment_image_base_pattern = f"comment_{comment_display_idx-1}_part_" # Use comment_display_idx-1 for 0-based image index
                      all_comment_parts = [img_path for img_path in post_image_files if comment_image_base_pattern in os.path.basename(img_path) and os.path.basename(img_path).endswith('.png')]

                      # Sort the image parts by their part index to ensure correct sequence
                      def sort_image_parts(img_path):
                          filename = os.path.basename(img_path)
                          match = re.search(r'_part_(\d+)\.png', filename)
                          return int(match.group(1)) if match else 0

                      matching_images = sorted(all_comment_parts, key=sort_image_parts)

                 # 디버그: 현재 오디오 세그먼트에 대해 찾은 이미지 목록 확인
                 logger.debug(f"오디오 세그먼트 {identifier}에 대해 찾은 매칭 이미지: {matching_images}")

                 if matching_images:
                      # Each matching image part will be displayed for the duration of the corresponding audio segment
                      # If there are multiple image parts for one audio segment, the audio duration is split equally
                       total_audio_duration_for_segment = audio_clip_duration_map.get(identifier, 0)
                       num_matching_images = len(matching_images)
                       duration_per_image = total_audio_duration_for_segment / num_matching_images if num_matching_images > 0 else 0

                       for img_path in matching_images:
                           image_duration_list_final.append((img_path, duration_per_image))
                           current_images.append(img_path)
                           logger.debug(f"이미지 {os.path.basename(img_path)}를 오디오 {identifier}에 매핑 - 초기 지속 시간: {duration_per_image:.2f}s")
                 else:
                      logger.warning(f"게시물 {post_id}의 오디오 세그먼트 {identifier}에 해당하는 이미지를 찾지 못했습니다. 이 오디오 세그먼트에는 이미지가 표시되지 않습니다.")

            # 모든 이미지 추가 후 총 오디오 길이에 맞춰 마지막 이미지 지속 시간 조정
            if processed_audio_clips:
                final_audio_clip = concatenate_audioclips(processed_audio_clips)
                total_audio_duration = final_audio_clip.duration
                total_image_initial_duration = sum([dur for img, dur in image_duration_list_final])

                # 길이 차이 계산
                duration_difference = total_audio_duration - total_image_initial_duration

                # 마지막 이미지 지속 시간 조정
                if image_duration_list_final:
                    last_image_index = len(image_duration_list_final) - 1
                    original_last_duration = image_duration_list_final[last_image_index][1]
                    adjusted_last_duration = max(0.01, original_last_duration + duration_difference) # Ensure duration is not zero or negative
                    image_duration_list_final[last_image_index] = (image_duration_list_final[last_image_index][0], adjusted_last_duration)
                    logger.debug(f"마지막 이미지 지속 시간 조정: {original_last_duration:.2f}s -> {adjusted_last_duration:.2f}s. 총 영상 길이 차이: {duration_difference:.2f}s")

                # 특정 지속 시간을 가진 이미지 시퀀스 클립 생성 (조정된 지속 시간 사용)
                images_in_order = [img_path for img_path, duration in image_duration_list_final]
                durations_in_order = [duration for img_path, duration in image_duration_list_final]

                if not images_in_order or not durations_in_order or len(images_in_order) != len(durations_in_order):
                    logger.error(f"게시물 {post_id}에 대한 이미지 및 조정된 지속 시간 목록 불일치. 영상 생성 불가.")
                else:
                     logger.info(f"게시물 {post_id}에 대해 {len(images_in_order)}개의 이미지로 이미지 시퀀스 클립 생성 중. 총 지속 시간: {sum(durations_in_order):.2f}s")
                     image_clip_sequence = ImageSequenceClip(images_in_order, durations=durations_in_order)

                     # 이 게시물에 대한 VideoGenerator.generate_video 메소드 호출
                     video_filename_base = post_id # 이 게시물에 대한 파일 이름 기본

                     # 이 게시물의 출력 디렉토리에 대한 VideoGenerator 초기화
                     video_gen_for_post = VideoGenerator(output_dir=post_video_output_dir)
                     # generate_video 호출 시 조정된 image_duration_list_final 사용
                     # 영상 생성 중 발생할 수 있는 예외 처리를 위해 try...except 블록 사용
                     try:
                         generated_video_path = video_gen_for_post.generate_video(image_duration_list_final, final_audio_clip, video_filename_base) # 파일 이름 기본 전달

                         if generated_video_path:
                             logger.info(f"게시물 {post_id}에 대한 영상 생성 성공: {generated_video_path}")
                             total_videos_generated += 1
                         else:
                             logger.error(f"게시물 {post_id}에 대한 영상 생성 실패.")

                     except Exception as e:
                         logger.error(f"게시물 {post_id} 영상 생성 중 오류 발생: {e}")

            # 처리된 오디오 클립이 없는 경우 (이전 로직 유지)
            else:
                logger.warning(f"게시물 {post_id}에 대한 처리된 오디오 클립이 없습니다. 영상에 오디오를 추가할 수 없습니다.")
                # 오디오 없이 영상 생성 또는 건너뛰기 (선택 사항)
                # 오디오 없이도 특정 지속 시간을 가진 이미지 시퀀스 클립 생성
                images_in_order = [img_path for img_path, duration in image_duration_list_final]
                durations_in_order = [duration for img_path, duration in image_duration_list_final]
                if images_in_order and durations_in_order and len(images_in_order) == len(durations_in_order):
                     logger.info(f"게시물 {post_id}에 대한 오디오 없는 영상 생성 중...")
                     image_clip_sequence = ImageSequenceClip(images_in_order, durations=durations_in_order)
                     video_gen_for_post = VideoGenerator(output_dir=post_video_output_dir) # 이 게시물의 출력 디렉토리에 대한 초기화
                     video_filename_base = f"{post_id}_shorts_no_audio"
                     generated_video_path = video_gen_for_post.generate_video(image_duration_list_final, None, video_filename_base) # audio_clip에 None 전달

                     if generated_video_path:
                         logger.warning(f"게시물 {post_id}에 대한 오디오 없는 영상 생성 완료: {generated_video_path}")
                     else:
                          logger.error(f"게시물 {post_id}에 대한 오디오 없는 영상 생성 실패.")
                else:
                    logger.warning(f"게시물 {post_id}에 대한 이미지 또는 지속 시간 누락으로 오디오 없는 영상 생성을 건너뜁니다.")

    logger.info("\n영상 생성 스크립트 완료.")
    logger.info(f"총 처리된 게시물 수: {total_posts_processed}")
    logger.info(f"총 생성된 영상 수: {total_videos_generated}")

    # 참고: 이미지 생성 시 임시 파일이 생성되었을 수 있지만, 현재 output/images의 이미지를 사용하므로 여기서 정리하지 않습니다.
    # 필요한 경우 ContentImageGenerator의 예시 사용법 또는 별도의 정리 스크립트에서 처리해야 합니다. 