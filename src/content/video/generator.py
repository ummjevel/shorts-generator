import os
import json
# moviepy는 설치 후 임포트 가능
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip # VideoFileClip 추가
import logging

logger = logging.getLogger(__name__)

class VideoGenerator:
    """
    이미지, 오디오, JSON 데이터를 사용하여 YouTube Shorts 영상을 생성하는 클래스
    """
    def __init__(self, image_dir: str, audio_path: str, json_path: str, output_path: str):
        """
        초기화
        :param image_dir: 이미지 파일들이 있는 디렉토리 경로
        :param audio_path: 오디오 파일 경로
        :param json_path: LLM 생성 결과 JSON 파일 경로
        :param output_path: 최종 영상이 저장될 경로
        """
        self.image_dir = image_dir
        self.audio_path = audio_path
        self.json_path = json_path
        self.output_path = output_path
        self.data = self._load_json_data()
        
        # 출력 디렉토리 생성
        output_dir = os.path.dirname(self.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"Created output directory: {output_dir}")


    def _load_json_data(self):
        """JSON 데이터를 로드합니다."""
        if not os.path.exists(self.json_path):
            logger.error(f"JSON file not found at {self.json_path}")
            return None
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Successfully loaded JSON data from {self.json_path}")
            return data
        except Exception as e:
            logger.error(f"Failed to load JSON data from {self.json_path}: {e}")
            return None

    def _get_image_files(self):
        """이미지 디렉토리에서 이미지 파일 목록을 가져옵니다."""
        if not os.path.isdir(self.image_dir):
            logger.error(f"Image directory not found or is not a directory: {self.image_dir}")
            return []
        
        # .jpg, .jpeg, .png 등 이미지 파일 확장자를 고려해야 하지만,
        # 여기서는 간단하게 파일 목록만 가져오고 정렬합니다.
        # 실제 구현 시에는 이미지 파일만 필터링하고 자연스러운 순서로 정렬하는 로직이 필요합니다.
        image_files = [os.path.join(self.image_dir, f) for f in os.listdir(self.image_dir) if os.path.isfile(os.path.join(self.image_dir, f))]
        # 파일 이름 순서대로 정렬 (예: image_001.png, image_002.png ...). 
        # 숫자로 정렬되도록 key 함수를 사용할 수 있지만, 기본 sort()도 많은 경우에 작동합니다.
        image_files.sort() 
        
        logger.info(f"Found {len(image_files)} image files in {self.image_dir}")
        return image_files

    def generate_shorts(self):
        """
        Shorts 영상을 생성합니다.
        """
        logger.info(f"Starting Shorts video generation for images in {self.image_dir}")

        image_files = self._get_image_files()
        if not image_files:
            logger.error("No image files found. Cannot generate video.")
            return False

        if not os.path.exists(self.audio_path):
            logger.error(f"Audio file not found at {self.audio_path}. Cannot generate video.")
            return False

        try:
            # 오디오 클립 로드
            audio_clip = AudioFileClip(self.audio_path)
            audio_duration = audio_clip.duration
            logger.info(f"Loaded audio clip from {self.audio_path} with duration {audio_duration:.2f} seconds.")

            num_images = len(image_files)
            if num_images == 0:
                 logger.error("No images to create video.")
                 return False
                 
            # 각 이미지가 보여질 시간 계산 (오디오 길이를 이미지 수로 나눔)
            # 최소 시간을 설정하거나, JSON 데이터를 활용한 더 복잡한 로직을 추가할 수 있습니다.
            duration_per_image = audio_duration / num_images
            logger.info(f"Each image will be displayed for {duration_per_image:.2f} seconds.")

            # 이미지 시퀀스를 영상 클립으로 생성
            # duration=duration_per_image 인자로 각 이미지 표시 시간을 설정합니다.
            video_clip = ImageSequenceClip(image_files, durations=[duration_per_image] * num_images)
            logger.info(f"Created image sequence clip with total duration {video_clip.duration:.2f} seconds.")
            
            # (TODO: 오디오 속도 조절 기능 추가 - 필요시 audio_clip.fx(vfx.speedx, factor=...) 사용)
            # 현재는 오디오 속도 조절 없이 진행합니다.

            # 영상 클립에 오디오 클립 설정
            final_clip = video_clip.set_audio(audio_clip)
            
            # 오디오 길이에 맞춰 영상 길이 조정 (필요하다면)
            # ImageSequenceClip의 duration 인자로 이미 설정했기 때문에 여기서는 생략 가능하지만,
            # 오디오가 더 길거나 짧은 경우 영상 길이를 맞추는 로직이 필요할 수 있습니다.
            # final_clip = final_clip.set_duration(audio_duration) 

            # 최종 영상 파일 저장
            # codec='libx264'는 MP4를 위한 일반적인 코덱입니다.
            # fps=24는 프레임 속도입니다. Shorts에 적합한 설정을 고려해야 합니다.
            # threads=4는 인코딩에 사용할 스레드 수입니다. 성능 개선에 도움이 될 수 있습니다.
            logger.info(f"Writing final video to {self.output_path}...")
            final_clip.write_videofile(self.output_path, codec='libx264', fps=24, threads=4)
            logger.info(f"Successfully generated Shorts video: {self.output_path}")

            return True

        except Exception as e:
            logger.error(f"An error occurred during video generation: {e}")
            return False


if __name__ == '__main__':
    # 예시 사용법 (실제 경로로 수정 필요)
    # logging.basicConfig(level=logging.INFO)
    # # 테스트를 위해 실제 이미지, 오디오, json 파일 경로를 지정해야 합니다.
    # IMAGE_DIR = 'path/to/your/images' # 예: './output/post_123/images'
    # AUDIO_PATH = 'path/to/your/audio.mp3' # 예: './output/post_123/audio.mp3'
    # JSON_PATH = 'path/to/your/data.json' # 예: './output/post_123/data.json'
    # OUTPUT_PATH = 'output/shorts_video.mp4' # 예: './output/post_123/shorts.mp4'

    # # 실제 파일들이 존재하는지 확인 필요
    # if os.path.exists(IMAGE_DIR) and os.path.exists(AUDIO_PATH) and os.path.exists(JSON_PATH):
    #     video_gen = VideoGenerator(
    #         image_dir=IMAGE_DIR,
    #         audio_path=AUDIO_PATH,
    #         json_path=JSON_PATH,
    #         output_path=OUTPUT_PATH
    #     )
    #     if video_gen.generate_shorts():
    #         logger.info("Video generation test successful.")
    #     else:
    #         logger.error("Video generation test failed.")
    # else:
    #     logger.error("Test files/directories not found. Please update paths.")
    pass 