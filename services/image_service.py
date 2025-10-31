"""
Image Service for Piu Application

This service handles all AI image generation logic (DALL-E, Imagen) and slideshow creation.
Business logic extracted from Piu.py to improve maintainability and testability.

Migration from Piu.py:
- DALL-E image generation
- Imagen image generation
- Prompt enhancement
- Image processing and saving
"""

import logging
import os
import time
from typing import Optional, List, Tuple, Callable
from io import BytesIO

# Optional imports with fallback
try:
    from openai import OpenAI, RateLimitError, AuthenticationError, APIConnectionError, APIStatusError, APITimeoutError
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    OpenAI = None
    RateLimitError = None
    AuthenticationError = None
    APIConnectionError = None
    APIStatusError = None
    APITimeoutError = None
    logging.warning("Thư viện OpenAI chưa được cài đặt. Chức năng DALL-E sẽ không hoạt động.")

try:
    from google import genai
    from google.genai import types, Client
    from google.api_core import exceptions as google_api_exceptions
    HAS_IMAGEN = True
except ImportError:
    HAS_IMAGEN = False
    genai = None
    types = None
    Client = None
    google_api_exceptions = None
    logging.warning("Thư viện google.genai chưa được cài đặt. Chức năng Imagen sẽ không hoạt động.")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None
    logging.warning("Thư viện PIL chưa được cài đặt. Chức năng xử lý ảnh sẽ bị hạn chế.")

# Import utilities
try:
    from utils.helpers import create_safe_filename
except ImportError:
    def create_safe_filename(text, max_length=50):
        """Fallback function if helper not available"""
        safe_text = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return safe_text[:max_length] if len(safe_text) > max_length else safe_text

# Constants
APP_NAME = "Piu"


class ImageService:
    """
    Service for AI image generation (DALL-E, Imagen) and slideshow creation.
    
    This service contains all business logic for image generation,
    separate from UI handling which remains in Piu.py.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize Image Service.
        
        Args:
            logger: Optional logger instance. If None, creates a new logger.
        """
        self.logger = logger or logging.getLogger(APP_NAME)
        self.logger.info("[ImageService] Initializing Image Service...")
    
    # ========================================================================
    # DALL-E METHODS
    # ========================================================================
    
    def generate_dalle_images(
        self,
        prompts: List[str],
        num_images: int,
        output_folder: str,
        api_key: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        stop_event: Optional[Callable[[], bool]] = None,
        max_retries: int = 2,
        retry_delay_seconds: float = 10.0
    ) -> Tuple[List[str], Optional[str]]:
        """
        Generate images using DALL-E API.
        
        Args:
            prompts: List of prompts for image generation
            num_images: Number of images to generate per prompt
            output_folder: Folder to save generated images
            api_key: OpenAI API key
            model: DALL-E model to use ("dall-e-2" or "dall-e-3")
            size: Image size (e.g., "1024x1024", "1792x1024", "1024x1792")
            quality: Image quality ("standard" or "hd")
            style: Image style ("vivid" or "natural")
            stop_event: Callable that returns True if processing should stop
            max_retries: Maximum number of retries on error
            retry_delay_seconds: Delay between retries
            
        Returns:
            Tuple of (saved_image_paths, error_message)
            - saved_image_paths: List of file paths to generated images
            - error_message: Error message string, or None on success
        """
        log_prefix = f"[DALL-E:{model}]"
        
        if not HAS_OPENAI or OpenAI is None:
            return [], "Thư viện OpenAI chưa được cài đặt."
        
        if not api_key:
            return [], "OpenAI API Key bị thiếu."
        
        saved_image_paths = []
        all_errors = []
        
        try:
            client = OpenAI(api_key=api_key, timeout=180.0)
            
            # Determine images per API call based on model
            if model == "dall-e-2":
                images_per_api_call = min(num_images, 10)  # DALL-E 2 can generate up to 10 images per call
            elif model == "dall-e-3":
                images_per_api_call = 1  # DALL-E 3 only generates 1 image per call
            else:
                images_per_api_call = 1
            
            # Process each prompt
            total_generated = 0
            # If we have multiple prompts, generate 1 image per prompt (or num_images if specified)
            # If we have 1 prompt, generate num_images with that prompt
            if len(prompts) == 1:
                # Single prompt: generate num_images with this prompt
                images_per_prompt = num_images
            else:
                # Multiple prompts: generate 1 image per prompt (or distribute num_images evenly)
                images_per_prompt = 1
            
            for prompt_idx, prompt in enumerate(prompts):
                if stop_event and stop_event():
                    return saved_image_paths, "Đã dừng bởi người dùng."
                
                # Calculate how many images to generate for this prompt
                if len(prompts) == 1:
                    # Single prompt mode: generate all num_images
                    remaining_images = num_images - total_generated
                    if remaining_images <= 0:
                        break
                    images_for_this_prompt = min(remaining_images, images_per_api_call if model == "dall-e-2" else num_images)
                else:
                    # Multiple prompts: generate 1 per prompt
                    remaining_images = num_images - total_generated
                    if remaining_images <= 0:
                        break
                    images_for_this_prompt = 1
                
                # Generate images with retry logic
                for attempt in range(max_retries + 1):
                    if stop_event and stop_event():
                        return saved_image_paths, "Đã dừng bởi người dùng."
                    
                    try:
                        self.logger.info(f"{log_prefix} Generating image {total_generated + 1}/{num_images} with prompt: '{prompt[:50]}...'")
                        
                        # Call DALL-E API
                        if model == "dall-e-3":
                            response = client.images.generate(
                                model=model,
                                prompt=prompt,
                                size=size,
                                quality=quality,
                                style=style,
                                n=1  # DALL-E 3 only supports n=1
                            )
                        else:  # dall-e-2
                            response = client.images.generate(
                                model=model,
                                prompt=prompt,
                                size=size,
                                n=images_for_this_prompt  # DALL-E 2 supports n up to 10
                            )
                        
                        # Download and save images
                        for img_data in response.data:
                            if stop_event and stop_event():
                                return saved_image_paths, "Đã dừng bởi người dùng."
                            
                            # Get image URL or b64_json
                            if hasattr(img_data, 'url') and img_data.url:
                                # Download from URL
                                import requests
                                img_response = requests.get(img_data.url, timeout=30)
                                img_response.raise_for_status()
                                image_bytes = img_response.content
                            elif hasattr(img_data, 'b64_json') and img_data.b64_json:
                                # Decode base64
                                import base64
                                image_bytes = base64.b64decode(img_data.b64_json)
                            else:
                                self.logger.warning(f"{log_prefix} Image data has no URL or b64_json")
                                continue
                            
                            # Save image
                            current_timestamp = int(time.time())
                            safe_prompt_part = create_safe_filename(prompt, max_length=30)
                            file_name = f"dalle_{model}_{safe_prompt_part}_{current_timestamp}_{len(saved_image_paths)+1}.png"
                            file_path = os.path.join(output_folder, file_name)
                            
                            os.makedirs(output_folder, exist_ok=True)
                            with open(file_path, "wb") as f:
                                f.write(image_bytes)
                            
                            saved_image_paths.append(file_path)
                            total_generated += 1
                            self.logger.info(f"{log_prefix} Saved image: {file_path}")
                        
                        # Success - break retry loop
                        break
                        
                    except (RateLimitError, APIConnectionError, APITimeoutError) as e:
                        if attempt < max_retries:
                            wait_time = retry_delay_seconds * (2 ** attempt)
                            self.logger.warning(f"{log_prefix} Retryable error (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {wait_time}s...")
                            if stop_event and stop_event():
                                return saved_image_paths, "Đã dừng bởi người dùng."
                            time.sleep(wait_time)
                        else:
                            error_msg = f"Lỗi API sau {max_retries + 1} lần thử: {e}"
                            all_errors.append(error_msg)
                            self.logger.error(f"{log_prefix} {error_msg}")
                    except Exception as e:
                        error_msg = f"Lỗi không mong đợi: {type(e).__name__} - {e}"
                        all_errors.append(error_msg)
                        self.logger.error(f"{log_prefix} {error_msg}", exc_info=True)
                        break  # Don't retry on unexpected errors
            
            if saved_image_paths:
                self.logger.info(f"{log_prefix} Successfully generated {len(saved_image_paths)} image(s)")
                error_message = None if not all_errors else "; ".join(all_errors)
                return saved_image_paths, error_message
            else:
                error_message = "Không tạo được ảnh nào. " + ("; ".join(all_errors) if all_errors else "Không có lỗi cụ thể.")
                return [], error_message
                
        except Exception as e:
            error_message = f"Lỗi nghiêm trọng: {type(e).__name__} - {e}"
            self.logger.error(f"{log_prefix} {error_message}", exc_info=True)
            return [], error_message
    
    # ========================================================================
    # IMAGEN METHODS
    # ========================================================================
    
    def generate_imagen_images(
        self,
        prompts: List[str],
        num_images_per_prompt: int,
        output_folder: str,
        api_key: str,
        aspect_ratio: str = "16:9",
        style_prompt_fragment: str = "",
        negative_prompt: str = "",
        stop_event: Optional[Callable[[], bool]] = None,
        max_retries_per_prompt: int = 2,
        retry_delay_seconds: float = 5.0,
        status_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[List[str], Optional[str]]:
        """
        Generate images using Imagen 3 API.
        
        Args:
            prompts: List of prompts for image generation
            num_images_per_prompt: Number of images to generate per prompt
            output_folder: Folder to save generated images
            api_key: Google Gemini API key (Imagen uses same API)
            aspect_ratio: Image aspect ratio (e.g., "16:9", "1:1", "9:16")
            style_prompt_fragment: Additional style keywords to append to prompts
            negative_prompt: Negative prompt (things to avoid)
            stop_event: Callable that returns True if processing should stop
            max_retries_per_prompt: Maximum retries per prompt on error
            retry_delay_seconds: Initial delay between retries
            status_callback: Optional callback to update status (e.g., "Đang vẽ ảnh 1/3...")
            
        Returns:
            Tuple of (saved_image_paths, error_message)
            - saved_image_paths: List of file paths to generated images
            - error_message: Error message string, or None on success
        """
        log_prefix = "[Imagen3]"
        
        if not HAS_IMAGEN or Client is None:
            return [], "Thư viện google.genai chưa được cài đặt."
        
        if not api_key:
            return [], "Gemini API Key bị thiếu (cần cho Imagen)."
        
        saved_image_paths = []
        all_errors = []
        
        try:
            client = Client(api_key=api_key)
            
            os.makedirs(output_folder, exist_ok=True)
            
            for i, prompt in enumerate(prompts):
                if stop_event and stop_event():
                    return saved_image_paths, "Đã dừng bởi người dùng."
                
                # Update status via callback (giống file gốc)
                if status_callback:
                    status_callback(f"🖼 Imagen: Đang chuẩn bị ảnh {i+1}/{len(prompts)}...")
                
                # Piu.py đã xử lý style_prompt_fragment, chỉ cần xử lý negative prompt ở đây
                # Prepare negative prompt
                default_negative_keywords = "text, words, letters, writing, typography, signs, banners, logos, watermark, signature, extra fingers, malformed hands, lowres, blurry"
                final_negative_prompt_str = default_negative_keywords
                if negative_prompt:
                    final_negative_prompt_str = f"{negative_prompt}, {default_negative_keywords}"
                
                # Combine everything into final prompt
                # Note: prompt đã có style_prompt_fragment từ Piu.py rồi
                final_prompt_for_api = f"{prompt.strip()} (without: {final_negative_prompt_str})"
                
                self.logger.info(f"{log_prefix} Generating {num_images_per_prompt} image(s) for prompt {i+1}/{len(prompts)}: '{prompt[:50]}...'")
                
                # Generate images with retry logic
                for attempt in range(max_retries_per_prompt + 1):
                    if stop_event and stop_event():
                        return saved_image_paths, "Đã dừng bởi người dùng."
                    
                    try:
                        # Create config
                        # Imagen 3.0 chỉ hỗ trợ sampleCount từ 1 đến 4
                        # Nếu num_images_per_prompt > 4, cần giới hạn về 4
                        safe_num_images = min(max(1, num_images_per_prompt), 4)
                        if num_images_per_prompt > 4:
                            self.logger.warning(f"{log_prefix} num_images_per_prompt ({num_images_per_prompt}) vượt quá giới hạn Imagen 3 (max=4). Sẽ sử dụng 4.")
                        
                        image_gen_config = types.GenerateImagesConfig(
                            number_of_images=safe_num_images,
                            aspect_ratio=aspect_ratio
                        )
                        
                        # Call Imagen API
                        response = client.models.generate_images(
                            model='imagen-3.0-generate-002',
                            prompt=final_prompt_for_api,
                            config=image_gen_config
                        )
                        
                        # Save images
                        for generated_image in response.generated_images:
                            if stop_event and stop_event():
                                return saved_image_paths, "Đã dừng bởi người dùng."
                            
                            # Get image bytes
                            image_bytes = generated_image.image.image_bytes
                            
                            # Save file
                            current_timestamp = int(time.time())
                            safe_prompt_part = create_safe_filename(prompt, max_length=30)
                            file_name = f"imagen3_{safe_prompt_part}_{current_timestamp}_{len(saved_image_paths)+1}.png"
                            file_path = os.path.join(output_folder, file_name)
                            
                            with open(file_path, "wb") as f:
                                f.write(image_bytes)
                            
                            saved_image_paths.append(file_path)
                            self.logger.info(f"{log_prefix} Saved image: {file_path}")
                        
                        # Success - break retry loop
                        break
                        
                    except Exception as e:
                        error_type = type(e).__name__
                        is_retryable = (
                            hasattr(google_api_exceptions, 'ResourceExhausted') and 
                            isinstance(e, google_api_exceptions.ResourceExhausted)
                        ) or (
                            hasattr(google_api_exceptions, 'ServiceUnavailable') and 
                            isinstance(e, google_api_exceptions.ServiceUnavailable)
                        )
                        
                        if is_retryable and attempt < max_retries_per_prompt:
                            wait_time = retry_delay_seconds * (2 ** attempt)
                            self.logger.warning(f"{log_prefix} Retryable error (attempt {attempt + 1}/{max_retries_per_prompt + 1}): {e}. Retrying in {wait_time}s...")
                            if stop_event and stop_event():
                                return saved_image_paths, "Đã dừng bởi người dùng."
                            time.sleep(wait_time)
                        else:
                            error_msg = f"Lỗi khi tạo ảnh cho prompt {i+1}: {error_type} - {e}"
                            all_errors.append(error_msg)
                            self.logger.error(f"{log_prefix} {error_msg}", exc_info=True)
                            break  # Move to next prompt
            
            if saved_image_paths:
                self.logger.info(f"{log_prefix} Successfully generated {len(saved_image_paths)} image(s)")
                error_message = None if not all_errors else "; ".join(all_errors)
                return saved_image_paths, error_message
            else:
                error_message = "Không tạo được ảnh nào. " + ("; ".join(all_errors) if all_errors else "Không có lỗi cụ thể.")
                return [], error_message
                
        except Exception as e:
            error_message = f"Lỗi nghiêm trọng: {type(e).__name__} - {e}"
            self.logger.error(f"{log_prefix} {error_message}", exc_info=True)
            return [], error_message

