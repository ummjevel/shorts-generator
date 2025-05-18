import os
import json
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from typing import Dict, List
import textwrap # Import textwrap for easier multiline handling
import re # Import regex for URL removal

# 색상 테마
COLOR_CYAN = (0, 153, 153)
COLOR_RED = (255, 51, 51)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0) # Add black for text for better contrast on white

class ContentImageGenerator:
    def __init__(self, width=720, height=1280, font_path=None, output_dir="output/images"):
        self.width = width
        self.height = height
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        # 기본 폰트 경로 (시스템 기본) - Fallback added
        if font_path is None:
             # Common paths for Arial Unicode on macOS, Windows, Linux
            common_font_paths = [
                "/Library/Fonts/Arial Unicode.ttf",
                "C:/Windows/Fonts/arialuni.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", # Common Linux font
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf" # Newer macOS path
            ]
            self.font_path = next((path for path in common_font_paths if os.path.exists(path)), None)
            if not self.font_path:
                 # Assuming logger is available from loguru import
                 # If running this class standalone without main block, logger might not be configured
                 try:
                     from loguru import logger
                     logger.warning("Arial Unicode or Liberation Sans not found. Using default font.")
                 except ImportError:
                     print("Warning: Arial Unicode or Liberation Sans not found and loguru not available. Using default font.")

        else:
            self.font_path = font_path

    def _get_font(self, size=40, bold=False):
        try:
            if self.font_path:
                # PIL doesn't directly support bold styles via truetype, need bold font file if available
                # For simplicity, just return the requested size for now.
                return ImageFont.truetype(self.font_path, size)
        except Exception:
             # Assuming logger is available from loguru import
             try:
                 from loguru import logger
                 logger.warning(f"Could not load font from {self.font_path}. Using default font.")
             except ImportError:
                  print(f"Warning: Could not load font from {self.font_path} and loguru not available. Using default font.")

             pass
        return ImageFont.load_default()

    def _wrap_text(self, text, font, max_width):
        # Use textwrap for simple wrapping
        # Estimate average character width for textwrap width calculation
        # This is a heuristic, true width depends on font and specific characters
        avg_char_width = font.size // 2 # Rough estimate
        chars_per_line = max_width // avg_char_width if avg_char_width > 0 else max_width
        chars_per_line = max(1, chars_per_line) # Ensure at least 1 char per line

        wrapper = textwrap.TextWrapper(width=chars_per_line, break_long_words=True)
        lines = []
        for paragraph in text.split('\n'):
             # Also handle wrapping of very long lines within the paragraph
            sub_lines = []
            current_line = ''
            words = paragraph.split(' ')
            for word in words:
                 test_line = (current_line + ' ' + word).strip()
                 # Use a dummy draw context for textbbox without drawing
                 temp_img = Image.new('RGB', (1, 1))
                 temp_draw = ImageDraw.Draw(temp_img)
                 bbox = temp_draw.textbbox((0, 0), test_line, font=font)
                 text_width = bbox[2] - bbox[0]
                 if text_width <= max_width:
                     current_line = test_line
                 else:
                     sub_lines.append(current_line)
                     current_line = word
            if current_line:
                sub_lines.append(current_line)
            lines.extend(sub_lines)

        return lines

    def _draw_multiline(self, draw, text, pos, font, fill, max_width, max_lines=None, line_spacing=10):
        # 텍스트를 max_width에 맞게 줄바꿈하여 여러 줄로 그림
        lines = self._wrap_text(text, font, max_width)

        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            # Add ellipsis to the last line
            last_line = lines[-1]
            ellipsis = "..."
            
            # Calculate space needed for ellipsis
            # Use a dummy draw context for textbbox without drawing
            temp_img = Image.new('RGB', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            ellipsis_bbox = temp_draw.textbbox((0,0), ellipsis, font=font)
            ellipsis_width = ellipsis_bbox[2] - ellipsis_bbox[0]

            # Calculate space available on the last line for text before ellipsis
            available_width = max_width - ellipsis_width

            # Truncate the last line if needed to fit the ellipsis
            while True:
                bbox = draw.textbbox((0, 0), last_line, font=font)
                text_width = bbox[2] - bbox[0]
                if text_width <= available_width or len(last_line) == 0:
                    break
                last_line = last_line[:-1]

            lines[-1] = last_line.strip() + ellipsis


        y = pos[1]
        drawn_lines_count = 0
        for line in lines:
            if max_lines is not None and drawn_lines_count >= max_lines: # Double check max lines limit
                 break
            draw.text((pos[0], y), line, font=font, fill=fill)
            y += font.size + line_spacing
            drawn_lines_count += 1
            
        return y # Return the final y position after drawing

    def _draw_header(self, draw, post: Dict, padding: int, header_height: int):
        """Draws the header section (subreddit, author, date)"""
        font_top = self._get_font(36)
        draw.text((padding, padding), f"r/{post.get('subreddit_name', '')}", fill=COLOR_WHITE, font=font_top)
        author_text = f"by {post.get('author', '')}"
        # Need a dummy draw context or calculate width manually for textbbox without drawing
        # A simple way is to use the same font and a temporary image/draw
        temp_img = Image.new('RGB', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        author_bbox = temp_draw.textbbox((0,0), author_text, font=font_top)
        author_width = author_bbox[2] - author_bbox[0]
        draw.text((self.width - author_width - padding, padding), author_text, fill=COLOR_WHITE, font=font_top)

        date_str = post.get('created_utc', '')
        date_disp = date_str[:10] if isinstance(date_str, str) and len(date_str) >= 10 else "N/A"
        font_date = self._get_font(24)
        draw.text((padding, padding + font_top.size + 5), date_disp, fill=COLOR_WHITE, font=font_date)

    def _draw_info_bar(self, draw, post: Dict, padding: int, info_bar_y: int, info_bar_height: int):
        """Draws the info bar (upvotes, comments count)"""
        font_info = self._get_font(32)
        upvotes = post.get('score', 0)
        comments_count = post.get('num_comments', 0)
        draw.text((padding, info_bar_y + padding//2), f"▲ {upvotes}", fill=COLOR_RED, font=font_info)
        draw.text((padding + 160, info_bar_y + padding//2), f"💬 {comments_count}", fill=COLOR_WHITE, font=font_info)

    def _find_image_url(self, post: Dict) -> str | None:
        """Attempts to find a suitable image URL in the post data."""
        # Prioritize url_overridden_by_dest if it exists and looks like an image
        url_dest = post.get('url_overridden_by_dest')
        if url_dest and isinstance(url_dest, str) and any(url_dest.lower().endswith(ext) for ext in ['.jpg', '.png', '.gif', '.jpeg']):
            return url_dest

        # Check preview images
        preview = post.get('preview')
        if preview and isinstance(preview, dict): # Check if preview exists and is a dictionary
            preview_images = preview.get('images', [])
            if preview_images and isinstance(preview_images, list):
                # Try to get the largest available preview image source from the first image in the list
                first_image = preview_images[0]
                if first_image and isinstance(first_image, dict):
                    source = first_image.get('source')
                    if source and isinstance(source, dict) and source.get('url'):
                        return source['url'].replace('&amp;', '&') # Clean up URL encoding

        # Fallback to the main URL if it looks like an image URL (less reliable)
        url = post.get('url')
        if url and isinstance(url, str) and any(url.lower().endswith(ext) for ext in ['.jpg', '.png', '.gif', '.jpeg']):
            return url

        # Add logging if no image URL is found
        try:
            from loguru import logger
            logger.debug(f"No suitable image URL found for post {post.get('id', 'unknown')}")
        except ImportError:
            print(f"Debug: No suitable image URL found for post {post.get('id', 'unknown')}")

        return None

    def _download_image(self, url: str) -> Image.Image | None:
        """Downloads an image from a URL and returns a Pillow Image object."""
        try:
            import requests
            response = requests.get(url, stream=True)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            img = Image.open(response.raw)
            return img
        except ImportError:
            try:
                from loguru import logger
                logger.error("Requests library not found. Cannot download images.")
            except ImportError:
                print("Error: Requests library not found. Cannot download images.")
            return None
        except Exception as e:
            try:
                from loguru import logger
                logger.error(f"Error downloading image from {url}: {e}")
            except ImportError:
                print(f"Error: Error downloading image from {url}: {e}")
            return None

    def _resize_image(self, image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """Resizes an image to fit within max_width and max_height while maintaining aspect ratio."""
        img_width, img_height = image.size
        aspect_ratio = img_width / img_height

        if img_width > max_width or img_height > max_height:
            # Calculate new dimensions maintaining aspect ratio
            if aspect_ratio > 1: # Wider than tall
                new_width = max_width
                new_height = int(new_width / aspect_ratio)
                if new_height > max_height:
                     new_height = max_height
                     new_width = int(new_height * aspect_ratio)
            else: # Taller than wide or square
                new_height = max_height
                new_width = int(new_height * aspect_ratio)
                if new_width > max_width:
                     new_width = max_width
                     new_height = int(new_width / aspect_ratio)

            # Ensure dimensions are positive integers
            new_width = max(1, int(new_width))
            new_height = max(1, int(new_height))

            # Use LANCZOS for high-quality downsampling
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            return resized_image
        else:
            # Image is already smaller than max dimensions, return as is
            return image

    @staticmethod # Make _remove_urls a static method
    def _remove_urls(text):
        """
        Removes URLs from a given text string.
        """
        # Simple regex to find URLs starting with http or https or www.
        # This might not catch all URLs, but covers most common cases.
        # Updated regex to be a bit more comprehensive for common URL patterns
        url_pattern = re.compile(r'\b(?:https?://|www\.)\S+|\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?\b')
        return url_pattern.sub('', text).strip() # Also strip whitespace left by removed URL

    def generate_post_only_image(self, post: Dict, idx=0, text_content="", image_type="", image_name_suffix=""):
        """Generate image with post title and body only."""
        img = Image.new("RGB", (self.width, self.height), COLOR_WHITE)
        draw = ImageDraw.Draw(img)

        padding = 30
        header_height = 100
        info_bar_height = 100
        footer_space = 50

        # 상단 바
        draw.rectangle([0, 0, self.width, header_height], fill=COLOR_CYAN)
        self._draw_header(draw, post, padding, header_height)

        # 제목
        title_start_y = header_height + padding
        # Determine title font size based on content
        has_body = text_content != ''
        # Safely determine if an image is available
        has_image = False
        try:
            image_url = self._find_image_url(post)
            has_image = image_url is not None
        except Exception as e:
            # Log error but assume no image is available for safety
            try:
                from loguru import logger
                logger.error(f"Error checking for image URL for post {post.get('id', 'unknown')}: {e}")
            except ImportError:
                print(f"Error: Error checking for image URL for post {post.get('id', 'unknown')}: {e}")

        if has_body or has_image:
            font_title_size = 38
        else:
            font_title_size = 48
        
        font_title = self._get_font(font_title_size)
        title_max_width = self.width - 2 * padding
        current_y = self._draw_multiline(draw, text_content, (padding, title_start_y), font_title, COLOR_BLACK, title_max_width, max_lines=None, line_spacing=15)
        current_y += padding # Add space below title

        # Find and add image if available
        image_url = self._find_image_url(post)
        if image_url:
            post_image = self._download_image(image_url)
            if post_image:
                # Calculate max area for image (below title, above potential body/info bar)
                info_bar_y = self.height - footer_space - info_bar_height
                # Available vertical space for image and body combined
                available_space_for_media_body = info_bar_y - current_y - padding # Add padding above info bar
                
                # Determine max image height, prioritizing taller images under specific conditions
                img_width, img_height = post_image.size
                aspect_ratio = img_width / img_height

                # Check body length condition
                body = text_content
                is_body_short_or_empty = len(body) <= 100

                # Condition to increase image size: taller image AND body is short or empty
                if aspect_ratio <= 1 and is_body_short_or_empty:
                    # Allow a larger max height
                    max_image_height = min(600, int(available_space_for_media_body * 0.8)) # Example values
                else:
                    # Use default max height otherwise
                    max_image_height = min(400, int(available_space_for_media_body * 0.6))

                max_image_width = self.width - 2 * padding

                if max_image_height > 50: # Ensure there's meaningful space for an image
                    try:
                        resized_post_image = self._resize_image(post_image, max_image_width, max_image_height)
                        
                        # Center the image horizontally
                        img_width, img_height = resized_post_image.size
                        img_x = padding + (max_image_width - img_width) // 2
                        img_y = current_y # Place image right after title space
                        
                        # Paste the image onto the background (handle transparency for PNGs)
                        if resized_post_image.mode == 'RGBA':
                            img.paste(resized_post_image, (img_x, img_y), resized_post_image)
                        else:
                            img.paste(resized_post_image, (img_x, img_y))
                        
                        current_y = img_y + img_height + padding # Update current_y after image
                        
                    except Exception as e:
                        # Log image processing error but continue
                        try:
                            from loguru import logger
                            logger.error(f"Error processing image for post {post.get('id', 'unknown')}: {e}")
                        except ImportError:
                            print(f"Error: Error processing image for post {post.get('id', 'unknown')}: {e}")
                else:
                    # Log if not enough space for image
                    try:
                        from loguru import logger
                        logger.debug(f"Not enough vertical space ({max_image_height}px) for image in post {post.get('id', 'unknown')}")
                    except ImportError:
                        print(f"Debug: Not enough vertical space ({max_image_height}px) for image in post {post.get('id', 'unknown')}")

        # Draw Body
        body = post.get('selftext', '').strip()
        if body:
            font_body = self._get_font(31)
            body_max_width = self.width - 2 * padding

            # Calculate available space for body before info bar
            info_bar_y = self.height - footer_space - info_bar_height
            max_body_end_y = info_bar_y - padding # Max Y for body to end, leaving padding space
            available_height_for_body = max_body_end_y - current_y

            body_max_lines = int(available_height_for_body / (font_body.size + 10)) if (available_height_for_body) > 0 else 0
            body_max_lines = max(0, body_max_lines) # Ensure non-negative

            current_y = self._draw_multiline(draw, body, (padding, current_y), font_body, COLOR_BLACK, body_max_width, max_lines=body_max_lines, line_spacing=10)
            current_y += padding # Add space below body

        # 하단 정보 (업보트/댓글 수) - 위치 고정
        info_bar_y = self.height - footer_space - info_bar_height
        draw.rectangle([0, info_bar_y, self.width, info_bar_y + info_bar_height], fill=COLOR_CYAN)
        self._draw_info_bar(draw, post, padding, info_bar_y, info_bar_height)

        # Save
        filename = f"post_{idx}_{post.get('id', 'unknown')}.png"
        filepath = os.path.join(self.output_dir, filename)
        img.save(filepath)
        return filepath

    def generate_comment_image_part(self, post: Dict, comment: Dict, wrapped_comment_lines: List[str], start_line_index: int, post_idx: int, comment_idx: int, part_idx: int) -> (str, int):
        """Generate an image for a part of a long comment."""
        img = Image.new("RGB", (self.width, self.height), COLOR_WHITE)
        draw = ImageDraw.Draw(img)

        padding = 30
        header_height = 100
        info_bar_height = 100
        footer_space = 50

        # 상단 바
        draw.rectangle([0, 0, self.width, header_height], fill=COLOR_CYAN)
        self._draw_header(draw, post, padding, header_height)

        # 제목
        title_start_y = header_height + padding
        # Determine title font size based on post content (same logic as post-only image)
        has_body = post.get('selftext', '').strip() != ''
        # Safely determine if an image is available
        has_image = False
        try:
            image_url = self._find_image_url(post)
            has_image = image_url is not None
        except Exception as e:
            # Log error but assume no image is available for safety
            try:
                from loguru import logger
                logger.error(f"Error checking for image URL for post {post.get('id', 'unknown')}: {e}")
            except ImportError:
                print(f"Error: Error checking for image URL for post {post.get('id', 'unknown')}: {e}")

        if has_body or has_image:
            font_title_size = 38
        else:
            font_title_size = 48
        
        font_title = self._get_font(font_title_size)
        title_max_width = self.width - 2 * padding
        current_y = self._draw_multiline(draw, post.get('title', ''), (padding, title_start_y), font_title, COLOR_BLACK, title_max_width, max_lines=None, line_spacing=15)
        current_y += padding # Add space below title

        # Draw Comment Part
        font_comment = self._get_font(36)
        comment_max_width = self.width - 2 * padding

        # Add image to comment part if available in comment data
        comment_image_url = None
        # Prioritize media_metadata if it exists and contains image info (e.g., gallery)
        comment_media_metadata = comment.get('media_metadata')
        if comment_media_metadata and isinstance(comment_media_metadata, dict):
            # Find the first image ID in media_metadata (structure can be complex, simplify for common cases)
            image_id = next(iter(comment_media_metadata)) if comment_media_metadata else None
            if image_id:
                # Construct a potential image URL from media_metadata (this structure varies!)
                # A common pattern for Reddit-hosted images in media_metadata might involve a URL like:
                # https://i.redd.it/{image_id}.jpg or .png
                # This is a heuristic and might need refinement based on actual data structure.
                # Let's try a common pattern:
                comment_image_url = f'https://i.redd.it/{image_id}.jpg' # Assume jpg for now, could check metadata for type
                # Further logic might be needed to check metadata['e']['m'] for mime type etc.
                # For simplicity, just try the jpg/png extensions on i.redd.it
                if not self._download_image(comment_image_url): # Try jpg
                    comment_image_url = f'https://i.redd.it/{image_id}.png' # Try png
                    if not self._download_image(comment_image_url): # Try png
                        comment_image_url = None # Neither worked

        # If media_metadata didn't yield an image, check the 'media' field
        if not comment_image_url:
            comment_media = comment.get('media')
            if comment_media and isinstance(comment_media, dict):
                # Check for 'oembed' structure common for embedded media (like Imgur, Gfycat via oembed)
                oembed = comment_media.get('oembed')
                if oembed and isinstance(oembed, dict):
                    comment_image_url = oembed.get('thumbnail_url') # Often includes thumbnail URL
                # Check for 'reddit_video' or 'image' type directly in media (less common for comments?)
                # This might overlap with gallery/media_metadata, but check anyway
                if not comment_image_url:
                     media_type = comment_media.get('type')
                     if media_type and 'image' in media_type:
                          # Direct image URL might be present, structure varies
                          comment_image_url = comment_media.get('content') # Heuristic guess
                          if not comment_image_url and 'url' in comment_media:
                               comment_image_url = comment_media.get('url') # Another heuristic guess

        comment_image = None
        if comment_image_url:
            comment_image = self._download_image(comment_image_url)

        # If comment_image is found, calculate space and draw it before comment text
        if comment_image:
             # Calculate max area for image within the comment section
             # Allocate some height for the image, leaving space for text
             info_bar_y = self.height - footer_space - info_bar_height
             max_comment_section_end_y = info_bar_y - padding
             available_space_for_media_and_text = max_comment_section_end_y - current_y

             # Allocate a portion of space for the image, e.g., max 300px height or 40% of available space
             max_comment_image_height = min(300, int(available_space_for_media_and_text * 0.4))
             max_comment_image_width = self.width - 2 * padding

             if max_comment_image_height > 50: # Ensure meaningful space
                  try:
                     resized_comment_image = self._resize_image(comment_image, max_comment_image_width, max_comment_image_height)
                     
                     # Center image horizontally within the content area
                     img_width, img_height = resized_comment_image.size
                     img_x = padding + (max_comment_image_width - img_width) // 2
                     img_y = current_y # Place image right after title/space

                     # Paste the image (handle transparency)
                     if resized_comment_image.mode == 'RGBA':
                         img.paste(resized_comment_image, (img_x, img_y), resized_comment_image)
                     else:
                         img.paste(resized_comment_image, (img_x, img_y))
                     
                     current_y = img_y + img_height + padding # Update current_y after image
                     
                  except Exception as e:
                        # Log image processing error but continue
                        try:
                            from loguru import logger
                            logger.error(f"Error processing comment image for post {post.get('id', 'unknown')}, comment {comment.get('id', 'unknown')}: {e}")
                        except ImportError:
                            print(f"Error: Error processing comment image for post {post.get('id', 'unknown')}, comment {comment.get('id', 'unknown')}: {e}")
             else:
                  # Log if not enough space for image
                  try:
                      from loguru import logger
                      logger.debug(f"Not enough vertical space ({max_comment_image_height}px) for comment image in post {post.get('id', 'unknown')}, comment {comment.get('id', 'unknown')}")
                  except ImportError:
                      print(f"Debug: Not enough vertical space ({max_comment_image_height}px) for comment image in post {post.get('id', 'unknown')}, comment {comment.get('id', 'unknown')}")

        # Comment background area calculations
        comment_draw_start_y = current_y # Start comment text/background from current_y (after image if any)

        # Available height for drawing comment lines
        info_bar_y = self.height - footer_space - info_bar_height
        max_comment_draw_end_y = info_bar_y - padding # Max Y before info bar
        available_draw_height = max_comment_draw_end_y - comment_draw_start_y

        text_start_y_in_bg = comment_draw_start_y + padding // 2
        available_text_height_in_bg = (max_comment_draw_end_y - (comment_draw_start_y)) - (padding) # Space for text within background
        available_text_height_in_bg = max(0, available_text_height_in_bg) # Ensure non-negative
        
        # Determine which lines fit in this part
        lines_drawn_count = 0
        current_draw_y = text_start_y_in_bg
        end_line_index = start_line_index # Initialize end index

        for i in range(start_line_index, len(wrapped_comment_lines)):
            line = wrapped_comment_lines[i]
            line_height = font_comment.size + 8
            if (current_draw_y - text_start_y_in_bg) + line_height <= available_text_height_in_bg:
                # This line fits
                current_draw_y += line_height
                lines_drawn_count += 1
                end_line_index = i + 1 # Next line index to start from
            else:
                break # This line does not fit, stop drawing

        # Draw the background based on how much text actually fits
        comment_bg_end_y = text_start_y_in_bg + (lines_drawn_count * (font_comment.size + 8)) + padding // 2 # Background ends after drawn text + bottom padding
        comment_bg_end_y = min(comment_bg_end_y, max_comment_draw_end_y) # Ensure background doesn't go past max allowed
        comment_bg_end_y = max(comment_bg_end_y, comment_draw_start_y + padding + font_comment.size + 8) # Ensure min height

        if comment_bg_end_y > comment_draw_start_y:
            draw.rectangle([0, comment_draw_start_y, self.width, comment_bg_end_y], fill=COLOR_CYAN)

            # Redraw the lines that fit, now with the correct background
            current_draw_y = text_start_y_in_bg
            for i in range(start_line_index, start_line_index + lines_drawn_count):
                line = wrapped_comment_lines[i]
                draw.text((padding, current_draw_y), line, font=font_comment, fill=COLOR_WHITE)
                current_draw_y += font_comment.size + 8

        # Add info bar at fixed bottom position
        info_bar_y = self.height - footer_space - info_bar_height
        draw.rectangle([0, info_bar_y, self.width, info_bar_y + info_bar_height], fill=COLOR_CYAN)
        self._draw_info_bar(draw, post, padding, info_bar_y, info_bar_height)

        # Save
        filename = f"post_{post_idx}_comment_{comment_idx}_part_{part_idx}.png"
        filepath = os.path.join(self.output_dir, filename)
        img.save(filepath)

        # Return filepath and the index of the next line to draw (or len if done)
        return filepath, end_line_index

    def generate_comment_image(self, post: Dict, comment: Dict, post_idx=0, comment_idx=0):
        """Generate image with post title and a single comment."""
        img = Image.new("RGB", (self.width, self.height), COLOR_WHITE)
        draw = ImageDraw.Draw(img)

        padding = 30
        header_height = 100
        info_bar_height = 100 # Used for calculating available space
        footer_space = 50 # Used for calculating available space

        # 상단 바
        draw.rectangle([0, 0, self.width, header_height], fill=COLOR_CYAN)
        self._draw_header(draw, post, padding, header_height)

        # 제목
        title_start_y = header_height + padding
        # Determine title font size based on post content (same logic as post-only image)
        has_body = post.get('selftext', '').strip() != ''
        # Safely determine if an image is available
        has_image = False
        try:
            image_url = self._find_image_url(post)
            has_image = image_url is not None
        except Exception as e:
            # Log error but assume no image is available for safety
            try:
                from loguru import logger
                logger.error(f"Error checking for image URL for post {post.get('id', 'unknown')}: {e}")
            except ImportError:
                print(f"Error: Error checking for image URL for post {post.get('id', 'unknown')}: {e}")

        if has_body or has_image:
            font_title_size = 38
        else:
            font_title_size = 48
        
        font_title = self._get_font(font_title_size)
        title_max_width = self.width - 2 * padding
        current_y = self._draw_multiline(draw, post.get('title', ''), (padding, title_start_y), font_title, COLOR_BLACK, title_max_width, max_lines=None, line_spacing=15)
        current_y += padding # Add space below title

        # Draw Comment
        # Format comment text with space after colon
        comment_text = f"{comment.get('author', '')}: {comment.get('body', '')}"
        font_comment = self._get_font(36) # Use body font size for comment for better readability
        comment_max_width = self.width - 2 * padding

        # Comment background area calculations
        comment_draw_start_y = current_y

        # Calculate required height for the full comment text
        wrapped_comment_lines = self._wrap_text(comment_text, font_comment, comment_max_width)
        required_comment_height = len(wrapped_comment_lines) * (font_comment.size + 8)

        # Comment background area ending Y position (required or max allowed)
        info_bar_y = self.height - footer_space - info_bar_height # Position of info bar (conceptual for space calculation)
        max_allowed_comment_bg_end_y = self.height - footer_space - info_bar_height - padding # Max Y before footer/info bar
        comment_preview_bg_end_y = min(comment_draw_start_y + required_comment_height + padding, max_allowed_comment_bg_end_y)
        comment_preview_bg_end_y = max(comment_preview_bg_end_y, comment_draw_start_y + padding + font_comment.size + 8) # Ensure min height

        if comment_preview_bg_end_y > comment_draw_start_y:
             draw.rectangle([0, comment_draw_start_y, self.width, comment_preview_bg_end_y], fill=COLOR_CYAN)

             # Draw comment text line by line to handle potential overflow
             text_start_y = comment_draw_start_y + padding // 2
             available_text_height = (comment_preview_bg_end_y - (comment_draw_start_y + padding // 2)) - (padding // 2) # Space for text, account for top/bottom padding
             
             lines_to_draw_indices = []
             current_text_height = 0
             
             # Determine how many lines fit in the current image
             fitting_lines_count = 0
             for i, line in enumerate(wrapped_comment_lines):
                 line_height = font_comment.size + 8
                 if current_text_height + line_height <= available_text_height:
                     lines_to_draw_indices.append(i)
                     current_text_height += line_height
                     fitting_lines_count += 1
                 else:
                     break # Stop if the next line doesn't fit

             drawn_lines_count = 0
             current_draw_y = text_start_y
             for i in lines_to_draw_indices:
                 line = wrapped_comment_lines[i]
                 draw.text((padding, current_draw_y), line, font=font_comment, fill=COLOR_WHITE)
                 current_draw_y += font_comment.size + 8
                 drawn_lines_count += 1

             # If there are remaining lines, generate additional images
             if fitting_lines_count < len(wrapped_comment_lines):
                 remaining_lines = wrapped_comment_lines[fitting_lines_count:]
                 # Recursive call or loop to generate next image(s)
                 # We need a way to pass the remaining lines and indicate this is a continuation
                 # Let's add a parameter to the method or create a helper
                 # For simplicity in this edit, let's add a conceptual call. 
                 # A better approach might be to return remaining lines or handle this loop in generate_from_json
                 # Let's refactor slightly to make generate_comment_image handle parts.
                 pass # Placeholder - actual multi-part logic needs more structure

        # Add info bar at fixed bottom position (optional for comment images?)
        # Decided to include info bar for consistency.
        info_bar_y = self.height - footer_space - info_bar_height
        draw.rectangle([0, info_bar_y, self.width, info_bar_y + info_bar_height], fill=COLOR_CYAN)
        self._draw_info_bar(draw, post, padding, info_bar_y, info_bar_height)

        # Save
        filename = f"post_{post_idx}_comment_{comment_idx}_{comment.get('id', 'unknown')}.png"
        filepath = os.path.join(self.output_dir, filename)
        img.save(filepath)
        return filepath

    def generate_from_json(self, json_path: str):
        """
        Reads post data from a JSON file and generates images for each post.
        This method is for generating all images from a collected data file.

        Args:
            json_file_path (str): Path to the JSON file containing Reddit post data.

        Returns:
            list[str]: List of paths to all generated image files.
        """
        all_image_paths = []
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if data is a list of posts or a dictionary containing posts
            if isinstance(data, list):
                posts = data
            elif isinstance(data, dict) and "posts" in data and isinstance(data["posts"], list):
                posts = data["posts"]
            else:
                print(f"Unexpected data format in {json_path}. Expected a list or a dictionary with a 'posts' key containing a list.")
                return []

            print(f"Generating images from {json_path}...")
            for index, post_data in enumerate(posts):
                self.current_post_index = index # Set current post index for filename consistency
                
                # --- Text Processing for TTS (Apply URL Removal here) ---
                # Extract text for TTS from title, body, and comments
                text_for_tts = post_data.get("title", "") + "\n\n" + post_data.get("body", "")
                for comment in post_data.get("comments", []):
                    # Apply URL removal and add comment author and body to TTS text
                    comment_author = comment.get('author', '') or '[Deleted]'
                    comment_body = comment.get('body', '') or ''
                    cleaned_comment_body = self._remove_urls(comment_body) # Apply URL removal for TTS text
                    if cleaned_comment_body:
                         text_for_tts += f"\n\n{comment_author}: {cleaned_comment_body}"

                # Clean the entire text for TTS by removing all URLs
                cleaned_text_for_tts = self._remove_urls(text_for_tts)
                
                # Now, pass cleaned_text_for_tts to your TTS module
                # Example (conceptual): save to a file that your TTS module reads
                # tts_output_dir = "output/audio_text"
                # os.makedirs(tts_output_dir, exist_ok=True)
                # post_id = post_data.get('id', f'unknown_{index}')
                # tts_text_filepath = os.path.join(tts_output_dir, f'{post_id}_tts_text.txt')
                # with open(tts_text_filepath, 'w', encoding='utf-8') as f:
                #     f.write(cleaned_text_for_tts)
                # print(f"Saved TTS text for post {post_id} to {tts_text_filepath}")
                # --- End Text Processing for TTS ---

                post_images = self.post_to_images(post_data)
                all_image_paths.extend(post_images)
            print(f"Finished image generation from {json_path}.")

        except Exception as e:
            print(f"Error generating images from {json_path}: {e}")

        return all_image_paths

    def post_to_images(self, post_data):
        """
        Generates a sequence of images for a given Reddit post.

        Args:
            post_data (dict): Dictionary containing post data (title, body, comments).

        Returns:
            list[str]: List of paths to the generated image files.
        """
        post_id = post_data.get("id", "")
        post_title = post_data.get("title", "N/A")
        post_body = post_data.get("body", "")
        comments = post_data.get("comments", [])

        if not post_id:
            print("Warning: Post data missing ID. Skipping image generation for this post.")
            return []

        # Clean up the title and body text - Add URL removal here
        cleaned_title = self._remove_urls(post_title)
        cleaned_body = self._remove_urls(post_body)

        # --- Image 1: Title ---
        # Use cleaned_title for image generation
        title_image_path = self.generate_post_only_image(
            post_data, # Pass the entire post data dictionary
            idx=self.current_post_index, # Use the stored post index
            text_content=cleaned_title,
            image_type="title", # Indicate this is for the title
            image_name_suffix="title_1" # Suffix for the filename
        )
        image_paths = [title_image_path] if title_image_path else []
        
        # --- Image 2+: Body (if exists) ---
        if cleaned_body:
            # Need to handle long body text potentially split into multiple images
            # For simplicity, let's generate one image for the body for now
            # In a real scenario, you'd split the body into chunks and generate an image for each chunk
            body_image_path = self.generate_post_only_image(
                post_data, # Pass the entire post data dictionary
                idx=self.current_post_index, # Use the stored post index
                text_content=cleaned_body,
                image_type="body", # Indicate this is for the body
                image_name_suffix="body_1" # Suffix for the filename
            )
            if body_image_path: image_paths.append(body_image_path)

        # --- Images 3+: Comments ---
        # Use the cleaned comment text - Add URL removal here for comments
        for i, comment in enumerate(comments):
            comment_text_raw = comment.get("body", "")
            cleaned_comment_text = self._remove_urls(comment_text_raw) # Apply URL removal to comment text
            
            # Skip comments that are empty after URL removal
            if not cleaned_comment_text:
                print(f"Skipping empty comment (after URL removal) at index {i} for post {post_id}")
                continue

            comment_id = comment.get("id", f"comment_{i}") # Use comment index if id is missing

            # Format comment text with author
            comment_author = comment.get('author', '') or '[Deleted]'
            formatted_comment_text = f"{comment_author}: {cleaned_comment_text}" # Use cleaned text here


            if formatted_comment_text:
                 # Again, a comment might be split into multiple images if long
                 # We will generate multiple images for long comments
                 font_comment = self._get_font(36)
                 padding = 30 # Ensure padding is defined
                 comment_max_width = self.width - 2 * padding

                 wrapped_comment_lines = self._wrap_text(formatted_comment_text, font_comment, comment_max_width)
                 
                 if not wrapped_comment_lines:
                     print(f"Skipping comment {comment_id} for post {post_id} as it resulted in no wrapped lines.")
                     continue

                 start_line_index = 0
                 part_idx = 1
                 while start_line_index < len(wrapped_comment_lines):
                     # Generate images for parts of the comment
                     filepath, next_start_line_index = self.generate_comment_image_part(
                         post_data, # Pass post data for header
                         comment, # Pass comment data
                         wrapped_comment_lines, # Pass the pre-wrapped lines
                         start_line_index,
                         post_idx=self.current_post_index, # Use the stored post index
                         comment_idx=i, # Use the comment index
                         part_idx=part_idx
                     )
                     if filepath: image_paths.append(filepath)
                     try:
                        from loguru import logger
                        logger.info(f"Generated comment image part {part_idx} for comment {comment_id} on post {post_id}: {filepath}")
                     except ImportError:
                        print(f"Generated comment image part {part_idx} for comment {comment_id} on post {post_id}: {filepath}")

                     start_line_index = next_start_line_index
                     part_idx += 1

        # Ensure images are sorted correctly (though filename should help)
        # The video generator handles the final sorting based on name
        
        return image_paths

# Assuming you have a sample JSON file in the output directory for testing
SAMPLE_JSON_PATH = 'output/AskReddit_20250514_093623.json' # Update this path as needed or create a sample file

if __name__ == "__main__":
    # Set up logging
    try:
        from loguru import logger
        logger.add("logs/generator.log", rotation="1 MB")
        logger.info("Content Image Generator script started.")
    except ImportError:
        print("Loguru not installed. Running without detailed logging.")
        logger = None # Or a simple dummy logger

    output_data_dir = 'output'
    output_images_base_dir = 'output/images'
    os.makedirs(output_images_base_dir, exist_ok=True)

    # Find all JSON files in the output data directory
    json_files = [f for f in os.listdir(output_data_dir) if f.endswith('.json')]

    if not json_files:
        if logger:
            logger.warning(f"No .json files found in {output_data_dir}.")
        print(f"No .json files found in {output_data_dir}.")
    else:
        if logger:
            logger.info(f"Found {len(json_files)} .json files in {output_data_dir}. Starting image generation per file.")
        print(f"Found {len(json_files)} .json files in {output_data_dir}. Starting image generation per file.")

        for json_file in json_files:
            json_path = os.path.join(output_data_dir, json_file)
            # Create a subdirectory in output/images based on the JSON filename (without extension)
            subdir_name = os.path.splitext(json_file)[0]
            output_subdir = os.path.join(output_images_base_dir, subdir_name)
            os.makedirs(output_subdir, exist_ok=True)

            if logger:
                logger.info(f"Processing {json_file}. Output images will be saved to {output_subdir}")
            print(f"Processing {json_file}. Output images will be saved to {output_subdir}")

            try:
                # Create a new generator instance for each JSON file, specifying the output subdirectory
                generator = ContentImageGenerator(output_dir=output_subdir)
                generator.generate_from_json(json_path)

                if logger:
                    logger.info(f"Finished processing {json_file}.")
                print(f"Finished processing {json_file}.")

            except Exception as e:
                if logger:
                    logger.error(f"An error occurred while processing {json_file}: {e}")
                print(f"An error occurred while processing {json_file}: {e}")
                # Continue to the next JSON file even if one fails

    if logger:
        logger.info("Content Image Generator script finished.")
    print("Content Image Generator script finished.") 