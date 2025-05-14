import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger

class RedditParser:
    def __init__(self, output_dir: str = "output", max_files_per_subreddit: int = 5):
        """Reddit 데이터 파서 초기화"""
        self.output_dir = Path(output_dir)
        self.max_files_per_subreddit = max_files_per_subreddit
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"RedditParser initialized with output directory: {output_dir}")

    def _cleanup_old_files(self, subreddit: str):
        """오래된 파일 정리"""
        try:
            # 서브레딧의 모든 파일 찾기
            pattern = f"{subreddit}_*.json"
            files = list(self.output_dir.glob(pattern))
            
            # 생성 시간 기준으로 정렬
            files.sort(key=lambda x: x.stat().st_mtime)
            
            # 최대 파일 수를 초과하는 오래된 파일 삭제
            while len(files) > self.max_files_per_subreddit:
                old_file = files.pop(0)
                old_file.unlink()
                logger.info(f"Deleted old file: {old_file}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {str(e)}")
            raise

    def save_posts(self, subreddit: str, posts: List[Dict[str, Any]]):
        """게시물 데이터 저장 (댓글 포함)"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{subreddit}_{timestamp}.json"
            filepath = self.output_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(posts, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Saved {len(posts)} posts to {filepath}")
            
            # 오래된 파일 정리
            self._cleanup_old_files(subreddit)
            
        except Exception as e:
            logger.error(f"Failed to save posts: {str(e)}")
            raise

    def load_posts(self, filepath: str) -> List[Dict[str, Any]]:
        """저장된 게시물 데이터 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                posts = json.load(f)
            logger.info(f"Loaded {len(posts)} posts from {filepath}")
            return posts
        except Exception as e:
            logger.error(f"Failed to load posts: {str(e)}")
            raise

    def get_latest_posts_file(self, subreddit: str) -> str:
        """특정 서브레딧의 가장 최근 게시물 파일 찾기"""
        try:
            files = list(self.output_dir.glob(f"{subreddit}_*.json"))
            if not files:
                return None
            latest_file = max(files, key=os.path.getctime)
            return str(latest_file)
        except Exception as e:
            logger.error(f"Failed to find latest posts file: {str(e)}")
            return None 