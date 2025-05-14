import praw
import os
from datetime import datetime
from loguru import logger
from typing import List, Dict, Any
from pathlib import Path

class RedditCollector:
    def __init__(self, 
                 post_limit: int = 10, 
                 min_upvotes: int = 100, 
                 time_filter: str = 'day', 
                 exclude_video_posts: bool = True):
        """Reddit 데이터 수집기 초기화 (.env 환경변수 사용)"""
        self.reddit = self._initialize_reddit()
        self.post_limit = post_limit
        self.min_upvotes = min_upvotes
        self.time_filter = time_filter
        self.exclude_video_posts = exclude_video_posts
        logger.info("RedditCollector initialized with environment variables")

    def _initialize_reddit(self) -> praw.Reddit:
        """Reddit API 클라이언트 초기화 (.env 환경변수 사용)"""
        try:
            reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                user_agent=os.getenv('REDDIT_USER_AGENT')
            )
            logger.info("Reddit API client initialized")
            return reddit
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {str(e)}")
            raise

    def get_hot_posts(self, subreddit_name: str, limit: int = None) -> List[Dict[str, Any]]:
        """특정 서브레딧의 인기 게시물 수집 (exclude_video_posts 옵션에 따라 비디오 게시물 제외)"""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            post_limit = limit or self.post_limit
            logger.info(f"Fetching {post_limit} posts from r/{subreddit_name}")
            for post in subreddit.hot(limit=post_limit):
                if post.score >= self.min_upvotes and (not self.exclude_video_posts or not post.is_video):
                    awards = []
                    if hasattr(post, 'all_awardings'):
                        awards = [{'name': award.name, 'count': award.count} for award in post.all_awardings]
                    media_info = post.media if hasattr(post, 'media') else None
                    preview_info = post.preview if hasattr(post, 'preview') else None
                    post_data = {
                        'id': post.id,
                        'title': post.title,
                        'score': post.score,
                        'url': post.url,
                        'created_utc': datetime.fromtimestamp(post.created_utc),
                        'num_comments': post.num_comments,
                        'permalink': post.permalink,
                        'selftext': post.selftext,
                        'is_video': post.is_video,
                        'is_self': post.is_self,
                        'author': str(post.author),
                        'subreddit_name': subreddit_name,
                        'upvote_ratio': post.upvote_ratio,
                        'awards': awards,
                        'url_overridden_by_dest': post.url_overridden_by_dest if hasattr(post, 'url_overridden_by_dest') else None,
                        'preview': preview_info,
                        'media': media_info,
                        'comments': self.get_post_comments(post.id, limit=5)
                    }
                    posts.append(post_data)
                    logger.debug(f"Collected post: {post.title} (score: {post.score}, awards: {len(awards)})")
            logger.info(f"Successfully collected {len(posts)} posts from r/{subreddit_name}")
            return posts
        except Exception as e:
            logger.error(f"Error collecting posts from r/{subreddit_name}: {str(e)}")
            raise

    def get_post_comments(self, post_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """특정 게시물의 인기 댓글 수집 (상위 5개, 고정 댓글 포함)"""
        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)
            comments = list(submission.comments.list())
            comments.sort(key=lambda x: x.score, reverse=True)
            top_comments = comments[:limit]
            comment_data_list = []
            for comment in top_comments:
                comment_data = {
                    'id': comment.id,
                    'body': comment.body,
                    'score': comment.score,
                    'created_utc': datetime.fromtimestamp(comment.created_utc),
                    'author': str(comment.author),
                    'is_submitter': comment.is_submitter,
                    'stickied': comment.stickied
                }
                comment_data_list.append(comment_data)
                logger.debug(f"Collected comment: {comment.id} (score: {comment.score}, stickied: {comment.stickied})")
            logger.info(f"Successfully collected {len(comment_data_list)} top comments for post {post_id}")
            return comment_data_list
        except Exception as e:
            logger.error(f"Error collecting comments for post {post_id}: {str(e)}")
            raise

    def collect_all_subreddits(self) -> Dict[str, List[Dict[str, Any]]]:
        """설정된 모든 서브레딧의 게시물 수집"""
        results = {}
        for subreddit in self.config['reddit']['subreddits']:
            try:
                posts = self.get_hot_posts(subreddit)
                results[subreddit] = posts
                logger.info(f"Collected {len(posts)} posts from r/{subreddit}")
            except Exception as e:
                logger.error(f"Failed to collect posts from r/{subreddit}: {str(e)}")
                continue
        return results 

    def collect_and_save_subreddit(self, subreddit_name: str, output_dir: str = "output"):
        """서브레딧의 인기 게시물과 각 게시물의 인기 댓글(5개)을 포함하여 하나의 파일로 저장"""
        try:
            # 게시물 수집 (댓글 포함)
            posts = self.get_hot_posts(subreddit_name)
            
            # 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{subreddit_name}_{timestamp}.json"
            output_path = Path(output_dir) / filename
            os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(posts, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Saved {len(posts)} posts (with comments) to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to collect and save subreddit {subreddit_name}: {str(e)}")
            raise 