import os
from dotenv import load_dotenv
load_dotenv()
from loguru import logger
from collector import RedditCollector
from parser import RedditParser
import yaml

def main():
    """메인 실행 함수"""
    try:
        # 설정 로드
        with open("config/config.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # RedditCollector 초기화
        collector = RedditCollector()
        parser = RedditParser()
        
        # 각 서브레딧에서 데이터 수집
        for subreddit in config['reddit']['subreddits']:
            try:
                # 게시물 수집 (댓글 포함)
                posts = collector.get_hot_posts(subreddit)
                
                # 데이터 저장
                parser.save_posts(subreddit, posts)
                
            except Exception as e:
                logger.error(f"Error processing subreddit {subreddit}: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main() 