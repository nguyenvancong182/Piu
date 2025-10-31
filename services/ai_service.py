"""
AI Service for Piu Application

This service handles all AI processing logic (Gemini, GPT, OpenAI).
Business logic extracted from Piu.py to improve maintainability and testability.

Migration from Piu.py:
- Gemini script editing and scene division
- GPT/OpenAI script editing and scene division
- API key validation
- Batch processing core logic
"""

import logging
import re
import time
from typing import Optional, Dict, Tuple, Callable

# Google API exceptions - import separately to avoid conflicts
try:
    from google.api_core import exceptions as google_exceptions
    from google.api_core.exceptions import GoogleAPICallError
    HAS_GOOGLE_EXCEPTIONS = True
except ImportError:
    HAS_GOOGLE_EXCEPTIONS = False
    google_exceptions = None
    GoogleAPICallError = None

# Optional imports with fallback
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    genai = None
    logging.warning("Thư viện google.generativeai chưa được cài đặt. Chức năng Gemini sẽ không hoạt động.")

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
    logging.warning("Thư viện OpenAI chưa được cài đặt. Chức năng GPT sẽ không hoạt động.")

# Import utilities
from utils.srt_utils import extract_dialogue_from_srt_string
from utils.helpers import sanitize_script_for_ai

# Constants
APP_NAME = "Piu"
AVAILABLE_GEMINI_MODELS = [
    "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
    "gemini-2.0-flash", "gemini-2.0-flash-lite",
    "gemini-1.5-pro-latest", "gemini-1.5-flash-latest"
]

AVAILABLE_GPT_MODELS = [
    "gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"
]


class AIService:
    """
    Service for AI processing (Gemini, GPT, OpenAI).
    
    This service contains all business logic for AI processing,
    separate from UI handling which remains in Piu.py.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize AI Service.
        
        Args:
            logger: Optional logger instance. If None, creates a new logger.
        """
        self.logger = logger or logging.getLogger(APP_NAME)
        self.logger.info("[AIService] Initializing AI Service...")
    
    # ========================================================================
    # GEMINI METHODS
    # ========================================================================
    
    def process_script_with_gemini(
        self,
        script_content: str,
        user_instruction: str,
        api_key: str,
        model_name: Optional[str] = None,
        stop_event: Optional[Callable[[], bool]] = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 20
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Process script editing with Gemini API.
        
        Args:
            script_content: Current script content to edit (can be empty for new scripts)
            user_instruction: User's instruction/prompt for editing
            api_key: Gemini API key
            model_name: Model name to use (if None, auto-selects)
            stop_event: Callable that returns True if processing should stop
            max_retries: Maximum number of retries on rate limit
            retry_delay_seconds: Initial delay between retries (doubles each time)
            
        Returns:
            Tuple of (processed_script, error_message)
            - processed_script: The edited script text, or None on error
            - error_message: Error message string, or None on success
        """
        log_prefix = "[GeminiScript]"
        self.logger.info(f"{log_prefix} Starting script processing with Gemini...")
        
        if not HAS_GEMINI or genai is None:
            return None, "Lỗi: Thư viện Google Generative AI chưa được cài đặt."
        
        if not api_key:
            return None, "Lỗi: Gemini API Key không được cung cấp."
        
        if stop_event and stop_event():
            return None, "Đã dừng bởi người dùng."
        
        processed_script = None
        error_message = None
        
        try:
            # Configure Gemini
            genai.configure(api_key=api_key)
            
            # Select model
            model = None
            if model_name:
                try:
                    model = genai.GenerativeModel(model_name)
                    self.logger.debug(f"{log_prefix} Using specified model: {model_name}")
                except Exception as e:
                    self.logger.warning(f"{log_prefix} Model {model_name} not available: {e}")
                    model_name = None
            
            # Auto-select model if not specified or failed
            if not model:
                model_names_to_try = AVAILABLE_GEMINI_MODELS if not model_name else [model_name]
                for mname in model_names_to_try:
                    try:
                        model = genai.GenerativeModel(mname)
                        self.logger.debug(f"{log_prefix} Auto-selected model: {mname}")
                        break
                    except Exception:
                        continue
                
                if not model:
                    # Fallback: try list_models
                    try:
                        models = genai.list_models()
                        if models:
                            first_model_name = models[0].name.split('/')[-1] if '/' in models[0].name else models[0].name
                            model = genai.GenerativeModel(first_model_name)
                            self.logger.debug(f"{log_prefix} Using fallback model: {first_model_name}")
                        else:
                            raise Exception("No models available")
                    except Exception as e:
                        return None, f"Không thể tìm thấy model Gemini khả dụng. Lỗi: {e}"
            
            # Check if input is SRT format and extract dialogue if needed
            is_input_srt = re.match(
                r"^\d+\s*[\r\n]+\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->",
                script_content.strip(),
                re.MULTILINE
            ) is not None
            
            text_to_send_to_ai = script_content
            if is_input_srt:
                self.logger.debug(f"{log_prefix} Input is SRT format, extracting dialogue...")
                text_to_send_to_ai = extract_dialogue_from_srt_string(script_content)
            
            # Build prompt
            action_type = "tạo mới" if not script_content.strip() else "biên tập"
            prompt_parts = [
                f"Bạn là một trợ lý AI chuyên {action_type} kịch bản cho video. Hãy thực hiện yêu cầu sau: '{user_instruction}'.",
                "Xin hãy giữ lại cấu trúc và số lượng dòng của văn bản gốc nếu có thể.",
                "QUAN TRỌNG: Chỉ trả về DUY NHẤT nội dung kịch bản đã xử lý, không thêm bất kỳ lời dẫn, giải thích hay định dạng markdown nào."
            ]
            
            if text_to_send_to_ai.strip():
                prompt_parts.append(f"\nNội dung kịch bản gốc để biên tập:\n---\n{text_to_send_to_ai}\n---")
            
            final_prompt = "\n".join(prompt_parts)
            
            # Retry loop for rate limits
            for attempt in range(max_retries + 1):
                if stop_event and stop_event():
                    return None, "Đã dừng bởi người dùng."
                
                try:
                    self.logger.info(f"{log_prefix} (Attempt {attempt + 1}/{max_retries + 1}) Sending request to Gemini...")
                    response = model.generate_content(final_prompt)
                    
                    if not response.candidates:
                        block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Không rõ"
                        raise RuntimeError(f"Yêu cầu đã bị chặn bởi bộ lọc an toàn của Gemini (Lý do: {block_reason}).")
                    
                    processed_script = response.text
                    self.logger.info(f"{log_prefix} Gemini processing completed successfully.")
                    error_message = None
                    break  # Success, exit retry loop
                    
                except google_exceptions.ResourceExhausted as e:
                    self.logger.warning(f"{log_prefix} (Attempt {attempt + 1}) Rate limit error: {e}")
                    if attempt < max_retries:
                        self.logger.info(f"{log_prefix} Will retry after {retry_delay_seconds} seconds...")
                        time.sleep(retry_delay_seconds)
                        retry_delay_seconds *= 2  # Exponential backoff
                    else:
                        error_message = f"Lỗi giới hạn (Rate Limit) sau {max_retries + 1} lần thử. Vui lòng đợi một lát hoặc kiểm tra gói cước của bạn."
                        break
                        
                except google_exceptions.PermissionDenied as e:
                    error_message = f"Lỗi xác thực Gemini: API Key không đúng hoặc không có quyền. Chi tiết: {e}"
                    self.logger.error(f"{log_prefix} {error_message}")
                    break
                    
                except Exception as e:
                    error_message = f"Lỗi khi gọi API Gemini: {type(e).__name__} - {e}"
                    self.logger.error(f"{log_prefix} {error_message}", exc_info=True)
                    break
            
            return processed_script, error_message
            
        except Exception as e:
            error_message = f"Lỗi không xác định: {type(e).__name__} - {e}"
            self.logger.error(f"{log_prefix} {error_message}", exc_info=True)
            return None, error_message
    
    def divide_scene_with_gemini(
        self,
        script_content: str,
        num_images: int,
        api_key: str,
        model_name: Optional[str] = None,
        character_sheet_text: str = "",
        formatted_srt_for_timing: Optional[str] = None,
        min_scene_duration_seconds: int = 0,
        auto_split_scenes: bool = False,
        art_style_name: str = "Mặc định (AI tự do)",
        art_style_prompt: str = "",
        cfg: Optional[Dict] = None,
        stop_event: Optional[Callable[[], bool]] = None,
        max_retries: int = 2,
        retry_delay_seconds: float = 15.0
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Divide script into scenes using Gemini API with JSON output format.
        
        Args:
            script_content: Script content to divide
            num_images: Number of images/scenes to create
            api_key: Gemini API key
            model_name: Model name to use (if None, auto-selects)
            character_sheet_text: Character sheet text for context
            formatted_srt_for_timing: SRT content for timing calculation (optional)
            min_scene_duration_seconds: Minimum duration per scene in seconds (0 = no limit)
            auto_split_scenes: Whether to auto-split scenes (if True, num_images is max)
            art_style_name: Art style name for image generation
            art_style_prompt: Art style prompt fragment
            cfg: Config dictionary (optional, for character sheet caching)
            stop_event: Callable that returns True if processing should stop
            max_retries: Maximum number of retries on errors
            retry_delay_seconds: Initial delay between retries
            
        Returns:
            Tuple of (response_text, error_message)
            - response_text: Gemini JSON response with scene division, or None on error
            - error_message: Error message string, or None on success
        """
        log_prefix = "[GeminiSceneDivision]"
        self.logger.info(f"{log_prefix} Starting scene division with Gemini...")
        
        if not HAS_GEMINI or genai is None:
            return None, "Lỗi: Thư viện Google Generative AI chưa được cài đặt."
        
        if not api_key:
            return None, "Lỗi: Gemini API Key không được cung cấp."
        
        # Sanitize script for AI (replace sensitive words)
        sanitized_script = sanitize_script_for_ai(script_content, cfg)
        
        if stop_event and stop_event():
            return None, "Đã dừng bởi người dùng."
        
        try:
            genai.configure(api_key=api_key)
            
            # Select model
            model = None
            if model_name:
                try:
                    model = genai.GenerativeModel(model_name)
                    self.logger.debug(f"{log_prefix} Using specified model: {model_name}")
                except Exception as e:
                    self.logger.warning(f"{log_prefix} Model {model_name} not available: {e}")
                    model_name = None
            
            if not model:
                for mname in AVAILABLE_GEMINI_MODELS:
                    try:
                        model = genai.GenerativeModel(mname)
                        self.logger.debug(f"{log_prefix} Auto-selected model: {mname}")
                        break
                    except Exception:
                        continue
            
            if not model:
                return None, "Không thể tìm thấy model Gemini khả dụng."
            
            # Import HarmCategory for safety settings
            try:
                from google.genai.types import HarmCategory, HarmBlockThreshold
            except ImportError:
                # Fallback if not available
                HarmCategory = None
                HarmBlockThreshold = None
            
            # Build character sheet instruction (if provided)
            character_instruction_block = ""
            natural_language_character_sheet = ""
            
            if character_sheet_text and cfg:
                use_character_sheet = cfg.get("imagen_use_character_sheet", False)
                if use_character_sheet:
                    source_of_cached_sheet = cfg.get("imagen_source_of_cached_sheet", None)
                    cached_optimized_sheet = cfg.get("imagen_cached_optimized_sheet", None)
                    
                    if character_sheet_text == source_of_cached_sheet and cached_optimized_sheet:
                        natural_language_character_sheet = cached_optimized_sheet
                        self.logger.debug(f"{log_prefix} Using cached optimized character sheet")
                    else:
                        # Optimize character sheet using AI (simplified - full logic in Piu.py)
                        # For now, use character_sheet_text directly
                        natural_language_character_sheet = character_sheet_text
                        self.logger.debug(f"{log_prefix} Using raw character sheet (optimization skipped)")
                    
                    if natural_language_character_sheet:
                        character_instruction_block = (
                            "\n\n**CHARACTER DESCRIPTIONS (HIGHEST PRIORITY):**\n"
                            "If a character from this list appears in a scene, you MUST use their description to create a consistent visual representation.\n"
                            f"--- CHARACTER SHEET ---\n{natural_language_character_sheet}\n--- END CHARACTER SHEET ---\n"
                        )
            
            # Build style instruction
            style_instruction_block = (
                "\n\n**ART STYLE INSTRUCTIONS:**\n"
                f"The final image prompts MUST strictly follow the user's chosen art style: '{art_style_name}'. "
                f"Incorporate these keywords and concepts: '{art_style_prompt}'. "
                "If the style is 'Mặc định (AI tự do)', you MUST prioritize photorealistic, highly detailed, cinematic 3D renders."
            )
            
            # Build safety instruction
            safety_instruction_block = (
                "**CRITICAL SAFETY MANDATE (HIGHEST PRIORITY):**\n"
                "You are a safety-conscious assistant. Your absolute primary goal is to generate text that is 100% safe for Google's most restrictive safety filters. "
                "All output MUST be SFW (Safe-for-Work).\n\n"
                "**FORBIDDEN CONTENT IN OUTPUT 'image_prompt':**\n"
                "- **ABSOLUTELY NO** direct descriptions of violence, gore, blood, or death.\n"
                "- **ABSOLUTELY NO** weapons in threatening poses or during use.\n"
                "- **ABSOLUTELY NO** sexually suggestive content, nudity, or hateful imagery.\n\n"
                "**SAFE REPHRASING STRATEGY:**\n"
                "When you encounter a sensitive scene, rephrase it using safe methods:\n"
                "1. Focus on Emotion & Aftermath\n"
                "2. Use Symbolism & Metaphor\n"
                "3. Focus on Tension & Environment\n"
            )
            
            # Build duration rules (if applicable)
            duration_rules_block = ""
            main_task_description = ""
            final_instruction = ""
            
            if min_scene_duration_seconds > 0 and formatted_srt_for_timing:
                # Calculate total duration from SRT
                # Simplified version - full calculation in Piu.py
                total_duration_seconds = 0  # Placeholder - should be calculated from SRT
                
                if total_duration_seconds > 0:
                    base_upper_bound = max(1, int(total_duration_seconds / min_scene_duration_seconds))
                    lower_bound_scenes = max(1, int(base_upper_bound * 0.5))
                    creative_upper_bound = max(base_upper_bound, int(base_upper_bound * 1.25))
                    
                    main_task_description = (
                        "You are a creative script analyst and director's assistant. You are processing a single, **continuous, and coherent narrative**. "
                        "Your primary task is to read this script and divide it into meaningful visual scenes. Your decisions must maintain character and story consistency across all scenes. "
                        "You must follow one strict rule, but otherwise have complete creative freedom to ensure the best narrative pacing."
                    )
                    
                    duration_rules_block = (
                        "\n\n**CRITICAL DURATION AND SCENE DIVISION RULES:**\n"
                        f"1. **The Hard Rule (Non-Negotiable):** Each 'scene_script' MUST represent a segment of AT LEAST **{min_scene_duration_seconds} seconds**. This is your only strict constraint.\n"
                        f"2. **Creative Guideline (For Reference Only):** Based on the script's length ({total_duration_seconds:.0f} seconds), similar projects often result in **{lower_bound_scenes} to {creative_upper_bound}** scenes. Consider this a general observation, NOT a target you must hit.\n"
                        "3. **Your Director's Judgment (Highest Priority):** Your main goal is to serve the story's rhythm and emotional impact. You have full authority to determine the final number of scenes."
                    )
                    
                    final_instruction = (
                        "Generate the JSON output. Strictly follow the minimum duration rule. "
                        "Use your creative judgment to select the best number of scenes for optimal storytelling."
                    )
            
            # Default task description if no duration limit
            if not main_task_description:
                if auto_split_scenes:
                    main_task_description = (
                        "You are an expert script analyst... You are processing a single, **continuous, and coherent narrative**. "
                        f"Your primary task is to read this script and divide it into the most important visual scenes that capture the story's essence. "
                        f"The number of scenes should be appropriate for the script's content, but MUST NOT EXCEED {num_images} scenes."
                    )
                    final_instruction = f"Generate the JSON output, dividing the script into a suitable number of scenes (up to a maximum of {num_images})."
                else:
                    main_task_description = (
                        "You are an expert script analyst... You are processing a single, **continuous, and coherent narrative**. "
                        f"Your primary task is to read this script and divide it into EXACTLY {num_images} key visual scenes."
                    )
                    final_instruction = f"Generate the JSON output, dividing the script into exactly {num_images} scenes."
            
            # Build system message
            system_message = (
                f"{main_task_description}"
                f"{safety_instruction_block}"
                f"{character_instruction_block}"
                f"{style_instruction_block}"
                f"{duration_rules_block}"
                "\n\n**OUTPUT FORMAT (CRITICAL):**\n"
                "- You MUST respond with a valid JSON array of objects. NO OTHER TEXT OR EXPLANATIONS.\n"
                "- Each object in the array represents one scene and MUST have two keys: 'scene_script' and 'image_prompt'.\n"
                "- The 'scene_script' value MUST be the EXACT, UNMODIFIED text segment from the original script that corresponds to the scene.\n"
                "- The 'image_prompt' value MUST be the concise, high-quality, safe-for-work image prompt in ENGLISH for that scene.\n"
                "- All image prompts must adhere to the art style instructions."
            )
            
            # Build user message with example
            user_message = (
                "Here is an example of the required JSON output format.\n"
                "SCRIPT INPUT:\n'Tiêu Viêm mỉm cười, nhìn về phía góc chợ. Ở đó, một cô gái thanh tú trong bộ váy xanh đang đứng đợi. Cô gái mỉm cười đáp lại.'\n"
                "EXPECTED JSON OUTPUT:\n"
                "[\n"
                "  {\n"
                '    "scene_script": "Tiêu Viêm mỉm cười, nhìn về phía góc chợ. Ở đó, một cô gái thanh tú trong bộ váy xanh đang đứng đợi.",\n'
                '    "image_prompt": "3D animation, ancient Chinese style. In a bustling marketplace, a handsome young man in a black robe named Tiêu Viêm smiles warmly as he looks towards a graceful girl in a green dress. cinematic lighting, rendered in Unreal Engine 5, text-free."\n'
                "  },\n"
                "  {\n"
                '    "scene_script": "Cô gái mỉm cười đáp lại.",\n'
                '    "image_prompt": "Close-up shot, 3D animation, ancient Chinese style. The graceful girl in the green dress smiles back, her eyes sparkling. soft lighting, detailed facial expression, text-free."\n'
                "  }\n"
                "]\n\n"
                "--- END OF EXAMPLE ---\n\n"
                "Now, process the following script based on ALL my instructions.\n"
                f"SCRIPT:\n\n{sanitized_script}\n\n"
                f"{final_instruction}"
            )
            
            final_prompt = f"{system_message}\n\n{user_message}"
            
            # Configure safety settings
            safety_settings = None
            if HarmCategory and HarmBlockThreshold:
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                }
            
            # Retry loop
            response_text = None
            error_message = None
            
            for attempt in range(max_retries + 1):
                if stop_event and stop_event():
                    return None, "Đã dừng bởi người dùng trước khi gọi API Gemini chia cảnh."
                
                try:
                    self.logger.info(f"{log_prefix} (Attempt {attempt + 1}/{max_retries + 1}) Calling Gemini API...")
                    
                    if safety_settings:
                        response = model.generate_content(final_prompt, safety_settings=safety_settings)
                    else:
                        response = model.generate_content(final_prompt)
                    
                    if stop_event and stop_event():
                        return None, "Đã dừng bởi người dùng sau khi API Gemini chia cảnh hoàn tất."
                    
                    if response.parts:
                        response_text = response.text.strip()
                        self.logger.info(f"{log_prefix} Scene division completed successfully.")
                        error_message = None
                        break  # Success
                    else:
                        block_reason = "Không rõ"
                        if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason'):
                            block_reason = response.prompt_feedback.block_reason.name
                        raise RuntimeError(f"Yêu cầu bị chặn bởi bộ lọc an toàn của Gemini (Lý do: {block_reason}).")
                    
                except (google_exceptions.ResourceExhausted, google_exceptions.ServiceUnavailable, 
                        google_exceptions.DeadlineExceeded, google_exceptions.InternalServerError) as e:
                    self.logger.warning(f"{log_prefix} (Attempt {attempt + 1}) Retryable error: {type(e).__name__}")
                    error_message = f"Lỗi tạm thời từ Google API: {type(e).__name__}."
                    
                    if attempt < max_retries:
                        self.logger.info(f"{log_prefix} Will retry after {retry_delay_seconds} seconds...")
                        time.sleep(retry_delay_seconds)
                        retry_delay_seconds *= 2  # Exponential backoff
                        continue
                    else:
                        break
                        
                except (RuntimeError, google_exceptions.PermissionDenied, google_exceptions.InvalidArgument) as e:
                    error_message = f"Lỗi không thể thử lại khi dùng Gemini chia cảnh: {e}"
                    self.logger.error(f"{log_prefix} {error_message}")
                    break
                    
                except Exception as e:
                    error_message = f"Lỗi không mong muốn khi dùng Gemini chia cảnh: {type(e).__name__} - {e}"
                    self.logger.error(f"{log_prefix} {error_message}", exc_info=True)
                    break
            
            return response_text, error_message
            
        except Exception as e:
            error_message = f"Lỗi khi gọi API Gemini: {type(e).__name__} - {e}"
            self.logger.error(f"{log_prefix} {error_message}", exc_info=True)
            return None, error_message
    
    def test_gemini_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Test if Gemini API key is valid.
        Enhanced version: Uses list_models() for primary check, then tries generate_content.
        
        Args:
            api_key: Gemini API key to test
            
        Returns:
            Tuple of (is_valid, status_message)
            - is_valid: True if key is valid, False otherwise
            - status_message: Human-readable status message
        """
        log_prefix = "[GeminiKeyTest]"
        self.logger.info(f"{log_prefix} Testing Gemini API key...")
        
        if not HAS_GEMINI or genai is None:
            return False, "Lỗi: Thư viện Google Generative AI chưa được cài đặt."
        
        if not api_key:
            return False, "Vui lòng nhập API Key."
        
        try:
            genai.configure(api_key=api_key)
            
            # Primary check: Try list_models() - more stable and doesn't require specific model
            self.logger.debug(f"{log_prefix} Attempting to check API key with list_models()...")
            models = genai.list_models()
            
            # Check if any models are available
            model_names = [m.name for m in models]
            self.logger.debug(f"{log_prefix} Number of available models: {len(model_names)}")
            
            if not model_names:
                raise Exception("Không tìm thấy model nào khả dụng.")
            
            # Try test generate_content with a model if possible (optional)
            tested_generate = False
            for preferred_model in ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro', 'gemini-1.5-pro-latest']:
                try:
                    # Find full model name from list
                    full_model_name = None
                    for m_name in model_names:
                        if preferred_model in m_name.lower():
                            full_model_name = m_name
                            break
                    
                    if full_model_name:
                        # Get short name from full name (e.g., models/gemini-1.5-pro -> gemini-1.5-pro)
                        short_name = full_model_name.split('/')[-1] if '/' in full_model_name else full_model_name
                        self.logger.debug(f"{log_prefix} Testing generate_content with model: {short_name}")
                        model = genai.GenerativeModel(short_name)
                        model.generate_content(
                            "test",
                            generation_config=genai.types.GenerationConfig(max_output_tokens=1, temperature=0.0)
                        )
                        tested_generate = True
                        self.logger.debug(f"{log_prefix} generate_content test successful with {short_name}")
                        break
                except Exception as test_e:
                    # Skip error for this model, try next
                    self.logger.debug(f"{log_prefix} Could not test with {preferred_model}: {test_e}")
                    continue
            
            if not tested_generate:
                self.logger.debug(f"{log_prefix} Could not test generate_content, but list_models() succeeded so API key is still valid.")
            
            # If list_models() succeeded, key and environment are both OK
            self.logger.info(f"{log_prefix} Gemini key check successful. Found {len(model_names)} available model(s).")
            return True, "✅ Key hợp lệ! (Kết nối thành công)"
                
        except google_exceptions.PermissionDenied as e:
            self.logger.warning(f"{log_prefix} Authentication error: {e}")
            return False, "Lỗi: Key không đúng hoặc không có quyền."
            
        except Exception as e:
            # Check if it's a GoogleAPICallError if available
            if GoogleAPICallError and isinstance(e, GoogleAPICallError):
                # This error could be due to network or other connection issues
                error_str = str(e)
                if "404" in error_str or "not found" in error_str.lower():
                    self.logger.warning(f"{log_prefix} Model not found error: {e}")
                    return False, "Lỗi: Model không khả dụng, nhưng API key có thể hợp lệ. Vui lòng thử lại."
                else:
                    self.logger.error(f"{log_prefix} Google API call error (possibly network): {e}")
                    return False, "Lỗi: Không kết nối được tới Google."
            else:
                # Generic exception handling
                self.logger.error(f"{log_prefix} Unexpected error testing key: {e}", exc_info=True)
                # Check if it's a header error for specific message
                if "illegal header value" in str(e).lower():
                    return False, "Lỗi: Key có vẻ đúng nhưng môi trường không hợp lệ (lỗi header)."
                else:
                    return False, f"Lỗi không xác định: {type(e).__name__}"
    
    # ========================================================================
    # GPT/OPENAI METHODS
    # ========================================================================
    
    def process_script_with_gpt(
        self,
        script_content: str,
        user_instruction: str,
        api_key: str,
        model_name: str = "gpt-3.5-turbo",
        stop_event: Optional[Callable[[], bool]] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Process script editing with GPT/OpenAI API.
        
        Args:
            script_content: Current script content to edit (can be empty for new scripts)
            user_instruction: User's instruction/prompt for editing
            api_key: OpenAI API key
            model_name: Model name to use
            stop_event: Callable that returns True if processing should stop
            
        Returns:
            Tuple of (processed_script, error_message)
            - processed_script: The edited script text, or None on error
            - error_message: Error message string, or None on success
        """
        log_prefix = f"[GPTScript:{model_name}]"
        self.logger.info(f"{log_prefix} Starting script processing with GPT...")
        
        if not HAS_OPENAI or OpenAI is None:
            return None, "Lỗi: Thư viện OpenAI chưa được cài đặt."
        
        if not api_key:
            return None, "Lỗi: OpenAI API Key không được cung cấp."
        
        if stop_event and stop_event():
            return None, "Đã dừng bởi người dùng."
        
        processed_script = None
        error_message = None
        
        try:
            client = OpenAI(api_key=api_key, timeout=180.0)
            
            # Check if input is SRT format
            is_input_srt = re.match(
                r"^\d+\s*[\r\n]+\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->",
                script_content.strip(),
                re.MULTILINE
            ) is not None
            
            text_to_send_to_ai = script_content
            if is_input_srt:
                self.logger.debug(f"{log_prefix} Input is SRT format, extracting dialogue...")
                text_to_send_to_ai = extract_dialogue_from_srt_string(script_content)
            
            # Build messages
            system_message = (
                "You are an AI assistant. Your task is to either generate new script content "
                "or edit existing script content based on the user's instructions. "
                "Return ONLY the resulting script content. Do not add any introductory phrases "
                "(e.g., 'Here is the edited script:'), concluding remarks, or explanations about your actions, "
                "unless the user's instruction explicitly asks for them. "
                "If generating new content, structure it clearly, often with each distinct idea or dialogue "
                "on a new line or new paragraph as appropriate for a script. "
                "If editing existing content, try to preserve the general structure (like line breaks between "
                "dialogue blocks) unless the instruction implies changes to structure (e.g., 'merge short sentences')."
            )
            
            user_message_parts = [f"User Instruction: \"{user_instruction}\"\n"]
            
            if text_to_send_to_ai.strip():
                user_message_parts.append(
                    f"\nPlease apply this instruction to the following existing script content. "
                    f"Remember to return only the modified script text.\n\n"
                    f"--- EXISTING SCRIPT CONTENT START ---\n"
                    f"{text_to_send_to_ai}\n"
                    f"--- EXISTING SCRIPT CONTENT END ---\n\n"
                    f"Processed Script Content:"
                )
            else:
                user_message_parts.append(
                    f"\nPlease generate the script content based on the instruction above. "
                    f"Remember to return only the generated script text.\n\n"
                    f"Generated Script Content:"
                )
            
            user_message = "".join(user_message_parts)
            
            if stop_event and stop_event():
                return None, "Đã dừng bởi người dùng."
            
            # Call API
            self.logger.info(f"{log_prefix} Sending request to OpenAI...")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=4000  # Adjust as needed
            )
            
            if not response.choices or not response.choices[0].message.content:
                return None, "OpenAI không trả về nội dung."
            
            processed_script = response.choices[0].message.content.strip()
            self.logger.info(f"{log_prefix} GPT processing completed successfully.")
            return processed_script, None
            
        except AuthenticationError as e:
            error_message = f"Lỗi xác thực OpenAI: API Key không đúng hoặc hết hạn. Chi tiết: {e}"
            self.logger.error(f"{log_prefix} {error_message}")
            return None, error_message
            
        except RateLimitError as e:
            error_message = f"Lỗi giới hạn yêu cầu OpenAI: Đã đạt giới hạn request. Chi tiết: {e}"
            self.logger.warning(f"{log_prefix} {error_message}")
            return None, error_message
            
        except (APIConnectionError, APITimeoutError) as e:
            error_message = f"Lỗi kết nối/timeout OpenAI: Không thể kết nối đến API. Chi tiết: {e}"
            self.logger.error(f"{log_prefix} {error_message}")
            return None, error_message
            
        except Exception as e:
            error_message = f"Lỗi khi gọi API OpenAI: {type(e).__name__} - {e}"
            self.logger.error(f"{log_prefix} {error_message}", exc_info=True)
            return None, error_message
    
    def divide_scene_with_gpt(
        self,
        script_content: str,
        num_images: int,
        api_key: str,
        model_name: str = "gpt-3.5-turbo",
        character_sheet_text: str = "",
        stop_event: Optional[Callable[[], bool]] = None
    ) -> Tuple[Optional[list], Optional[str]]:
        """
        Divide script into scenes using GPT API and return list of DALL-E prompts.
        
        Args:
            script_content: Script content to divide (can be SRT format)
            num_images: Number of images/scenes to create
            api_key: OpenAI API key
            model_name: Model name to use
            character_sheet_text: Character sheet text for context (unused for now)
            stop_event: Callable that returns True if processing should stop
            
        Returns:
            Tuple of (prompt_list, error_message)
            - prompt_list: List of DALL-E prompts, or None on error
            - error_message: Error message string, or None on success
        """
        log_prefix = f"[GPTSceneDivision:{model_name}]"
        self.logger.info(f"{log_prefix} Starting scene division with GPT...")
        
        if not HAS_OPENAI or OpenAI is None:
            return None, "Lỗi: Thư viện OpenAI chưa được cài đặt."
        
        if not api_key:
            return None, "Lỗi: OpenAI API Key không được cung cấp."
        
        if stop_event and stop_event():
            return None, "Đã dừng bởi người dùng."
        
        try:
            client = OpenAI(api_key=api_key, timeout=180.0)
            
            # Check if input is SRT format and extract dialogue if needed
            is_input_srt = re.match(
                r"^\d+\s*[\r\n]+\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->",
                script_content.strip(),
                re.MULTILINE
            ) is not None
            
            text_to_send_to_ai = script_content
            if is_input_srt:
                self.logger.debug(f"{log_prefix} Input is SRT format, extracting dialogue...")
                text_to_send_to_ai = extract_dialogue_from_srt_string(script_content)
            
            # Build system message
            system_message = (
                "Bạn là một trợ lý AI chuyên phân tích kịch bản và tạo mô tả hình ảnh an toàn, phù hợp với mọi đối tượng, "
                "với mục tiêu tạo ra hình ảnh chân thực và sắc nét. "
                "Nhiệm vụ của bạn là đọc hiểu kịch bản được cung cấp, sau đó chia nó thành một số lượng phân cảnh hoặc "
                "khoảnh khắc quan trọng đã được chỉ định. "
                "Với mỗi phân cảnh, bạn phải tạo ra một prompt mô tả hình ảnh ngắn gọn, súc tích (bằng tiếng Anh, "
                "tối đa khoảng 40-60 từ) phù hợp cho một AI tạo hình ảnh như DALL-E. "
                "Mỗi prompt DALL-E nên tập trung nắm bắt được bản chất hình ảnh của phân cảnh tương ứng: bối cảnh, "
                "ngoại hình/hành động nổi bật của nhân vật (nếu có), đối tượng quan trọng, và không khí/cảm xúc của cảnh. "
                "QUAN TRỌNG VỀ PHONG CÁCH ẢNH: "
                "1. Ưu tiên phong cách TẢ THỰC, CHI TIẾT CAO, như ảnh chụp chất lượng cao hoặc render 3D điện ảnh. "
                "2. TRỪ KHI KỊCH BẢN GỐC YÊU CẦU RÕ RÀNG một phong cách khác, hãy MẶC ĐỊNH hướng tới phong cách CHÂN THỰC 3D. "
                "3. Sử dụng các từ khóa như: 'photorealistic', 'hyperrealistic', 'highly detailed', 'sharp focus', "
                "'3D render', 'cinematic lighting', 'Unreal Engine 5 style', 'V-Ray render', 'octane render', "
                "'detailed skin texture', 'intricate details', 'professional photography', '8K resolution'. "
                "QUAN TRỌNG VỀ AN TOÀN NỘI DUNG: Tất cả các prompt DALL-E phải TUÂN THỦ NGHIÊM NGẶT chính sách nội dung. "
                "TRÁNH TUYỆT ĐỐI các mô tả có thể bị coi là bạo lực, người lớn, thù địch, tự hại, hoặc lừa đảo. "
                "TRÁNH đưa lời thoại, tên nhân vật đang nói vào prompt DALL-E. "
                "ĐẶC BIỆT LƯU Ý: Các prompt DALL-E phải hướng dẫn DALL-E KHÔNG ĐƯỢC VIẾT BẤT KỲ CHỮ, KÝ TỰ, HAY VĂN BẢN nào. "
                "Thêm các cụm từ như 'no text', 'text-free', 'image only, no writing', 'avoid typography', 'typography-free'."
            )
            
            # Build user message
            user_message = (
                f"Dưới đây là một kịch bản:\n\n"
                f"```script\n{text_to_send_to_ai}\n```\n\n"
                f"Dựa vào kịch bản trên, hãy chia nó thành đúng {num_images} phân cảnh hoặc khoảnh khắc hình ảnh quan trọng. "
                f"Sau đó, với mỗi phân cảnh, hãy tạo một prompt bằng tiếng Anh để DALL-E vẽ ảnh minh họa. "
                f"Yêu cầu quan trọng: Chỉ trả về {num_images} prompt DALL-E này, mỗi prompt trên một dòng mới. "
                f"Không thêm bất kỳ giải thích, đánh số, hay định dạng nào khác ngoài các dòng prompt này."
            )
            
            if stop_event and stop_event():
                return None, "Đã dừng bởi người dùng."
            
            # Call API
            self.logger.info(f"{log_prefix} Sending request to OpenAI to create {num_images} DALL-E prompts...")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.5,
            )
            
            if not response.choices or not response.choices[0].message.content:
                return None, "OpenAI không trả về nội dung."
            
            gpt_response_content = response.choices[0].message.content.strip()
            self.logger.info(f"{log_prefix} GPT response received (length: {len(gpt_response_content)} chars)")
            
            # Parse response into list of prompts
            list_of_prompts = []
            raw_prompts = gpt_response_content.splitlines()
            for p_line in raw_prompts:
                p_line_stripped = p_line.strip()
                if p_line_stripped:
                    list_of_prompts.append(p_line_stripped)
            
            if not list_of_prompts:
                return None, "GPT không trả về DALL-E prompt nào hoặc định dạng không đúng."
            
            if len(list_of_prompts) != num_images:
                self.logger.warning(
                    f"{log_prefix} GPT returned {len(list_of_prompts)} prompts, but requested {num_images}. "
                    f"Will use what we got."
                )
            
            self.logger.info(f"{log_prefix} Extracted {len(list_of_prompts)} DALL-E prompt(s).")
            return list_of_prompts, None
            
        except AuthenticationError as e:
            error_message = f"Lỗi xác thực OpenAI: API Key không đúng hoặc hết hạn. Chi tiết: {e}"
            self.logger.error(f"{log_prefix} {error_message}")
            return None, error_message
            
        except RateLimitError as e:
            error_message = f"Lỗi giới hạn yêu cầu OpenAI: Đã đạt giới hạn request. Chi tiết: {e}"
            self.logger.warning(f"{log_prefix} {error_message}")
            return None, error_message
            
        except (APIConnectionError, APITimeoutError) as e:
            error_message = f"Lỗi kết nối/timeout OpenAI: Không thể kết nối đến API. Chi tiết: {e}"
            self.logger.error(f"{log_prefix} {error_message}")
            return None, error_message
            
        except APIStatusError as e:
            status_code = e.status_code if hasattr(e, 'status_code') else 'N/A'
            err_msg = e.message if hasattr(e, 'message') else str(e)
            error_message = f"Lỗi từ API OpenAI (Mã: {status_code}): {err_msg}"
            self.logger.error(f"{log_prefix} {error_message}")
            return None, error_message
            
        except Exception as e:
            error_message = f"Lỗi khi gọi API OpenAI: {type(e).__name__} - {e}"
            self.logger.error(f"{log_prefix} {error_message}", exc_info=True)
            return None, error_message
    
    def translate_with_openai(
        self,
        text_list: list,
        target_lang: str,
        api_key: str,
        source_lang: Optional[str] = None,
        translation_style: str = "Mặc định (trung tính)",
        model_name: str = "gpt-3.5-turbo",
        stop_event: Optional[Callable[[], bool]] = None
    ) -> Tuple[Optional[list], Optional[str]]:
        """
        Translate text list using OpenAI API.
        
        Args:
            text_list: List of texts to translate
            target_lang: Target language code (e.g., 'vi', 'en', 'Vietnamese', 'English')
            api_key: OpenAI API key
            source_lang: Source language code (optional, 'auto' or None for auto-detect)
            translation_style: Translation style (e.g., 'Mặc định (trung tính)', 'Cổ trang (historical/ancient)')
            model_name: Model name to use
            stop_event: Callable that returns True if processing should stop
            
        Returns:
            Tuple of (translated_list, error_message)
            - translated_list: List of translated texts, or None on error
            - error_message: Error message string, or None on success
        """
        log_prefix = "[OpenAITranslate]"
        self.logger.info(f"{log_prefix} Starting translation with OpenAI...")
        
        if not HAS_OPENAI or OpenAI is None:
            return None, "Lỗi: Thư viện OpenAI chưa được cài đặt."
        
        if not api_key:
            return None, "Lỗi: OpenAI API Key không được cung cấp."
        
        translated_texts = []
        num_lines = len(text_list)
        source_lang_name = source_lang if source_lang and source_lang != 'auto' else "the original language"
        
        # Determine style instruction for prompt
        style_instruction = f"in a '{translation_style}' style"
        if "Mặc định" in translation_style or translation_style.lower() == "neutral":
            style_instruction = "in a neutral style"
        elif "Cổ trang" in translation_style:
            style_instruction = "in a style suitable for historical or ancient contexts (e.g., historical drama, classic literature)"
        
        self.logger.info(f"{log_prefix} Translating {num_lines} lines to '{target_lang}' (Style: {translation_style})...")
        
        try:
            client = OpenAI(api_key=api_key, timeout=60.0)
            
            for i, text_to_translate in enumerate(text_list):
                if stop_event and stop_event():
                    self.logger.warning(f"{log_prefix} Stop event detected during translation.")
                    return translated_texts  # Return what we have so far
                
                if not text_to_translate.strip():
                    translated_texts.append("")
                    continue
                
                # Build prompt
                prompt_message = (
                    f"You are a highly skilled translator. Translate the following text "
                    f"from {source_lang_name} to {target_lang} {style_instruction}. "
                    f"IMPORTANT: Respond ONLY with the translated text itself, without any introductory phrases, "
                    f"explanations, quotation marks, or markdown formatting."
                    f"\n\nText to translate:\n---\n{text_to_translate}\n---"
                    f"\n\nTranslated text:"
                )
                
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "user", "content": prompt_message}
                        ],
                        temperature=0.2,
                        max_tokens=int(len(text_to_translate) * 2.5) + 60,
                    )
                    
                    translated_line = response.choices[0].message.content.strip()
                    
                    # Remove quotes if AI wrapped the response
                    if translated_line.startswith('"') and translated_line.endswith('"'):
                        translated_line = translated_line[1:-1].strip()
                    
                    translated_texts.append(translated_line)
                    time.sleep(0.3)  # Small delay between requests
                    
                except Exception as api_call_error:
                    self.logger.error(f"{log_prefix} Error translating line {i+1}: {api_call_error}")
                    # Keep original text if translation fails
                    translated_texts.append(text_to_translate)
                    time.sleep(1)
            
            self.logger.info(f"{log_prefix} Translation completed. Translated {len(translated_texts)} lines.")
            return translated_texts, None
            
        except AuthenticationError as e:
            error_message = f"Lỗi xác thực OpenAI: API Key không đúng hoặc hết hạn. Chi tiết: {e}"
            self.logger.error(f"{log_prefix} {error_message}")
            return None, error_message
            
        except RateLimitError as e:
            error_message = f"Lỗi giới hạn yêu cầu OpenAI: Đã đạt giới hạn request. Chi tiết: {e}"
            self.logger.warning(f"{log_prefix} {error_message}")
            return None, error_message
            
        except (APIConnectionError, APITimeoutError) as e:
            error_message = f"Lỗi kết nối/timeout OpenAI: Không thể kết nối đến API. Chi tiết: {e}"
            self.logger.error(f"{log_prefix} {error_message}")
            return None, error_message
            
        except Exception as e:
            error_message = f"Lỗi khi gọi API OpenAI: {type(e).__name__} - {e}"
            self.logger.error(f"{log_prefix} {error_message}", exc_info=True)
            return None, error_message
    
    def test_openai_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Test if OpenAI API key is valid.
        
        Args:
            api_key: OpenAI API key to test
            
        Returns:
            Tuple of (is_valid, status_message)
            - is_valid: True if key is valid, False otherwise
            - status_message: Human-readable status message
        """
        log_prefix = "[OpenAIKeyTest]"
        self.logger.info(f"{log_prefix} Testing OpenAI API key...")
        
        if not HAS_OPENAI or OpenAI is None:
            return False, "Lỗi: Thư viện OpenAI chưa được cài đặt."
        
        if not api_key:
            return False, "Vui lòng nhập API Key."
        
        try:
            test_client = OpenAI(api_key=api_key, timeout=15.0)
            
            # Try a small chat completion call
            response = test_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                temperature=0
            )
            
            if response.choices and response.choices[0].message.content:
                self.logger.info(f"{log_prefix} OpenAI API key is valid.")
                return True, "Key hợp lệ! (Kết nối thành công)"
            else:
                return False, "Key hợp lệ nhưng không nhận được phản hồi."
                
        except AuthenticationError as e:
            self.logger.warning(f"{log_prefix} Authentication error: {e}")
            return False, "Lỗi: Key không đúng hoặc hết hạn."
            
        except RateLimitError as e:
            self.logger.warning(f"{log_prefix} Rate limit error: {e}")
            return False, "Lỗi: Vượt quá giới hạn request."
            
        except (APIConnectionError, APITimeoutError) as e:
            self.logger.error(f"{log_prefix} Connection/timeout error: {e}")
            return False, "Lỗi: Không kết nối được OpenAI."
            
        except APIStatusError as e:
            self.logger.error(f"{log_prefix} API status error: {e.status_code}")
            if "does not exist or you do not have access to it" in str(e).lower():
                return False, "Lỗi: Key đúng, nhưng không có quyền truy cập model."
            return False, f"Lỗi API OpenAI: {e.status_code}"
            
        except Exception as e:
            self.logger.error(f"{log_prefix} Error testing key: {e}", exc_info=True)
            return False, f"Lỗi không xác định: {e}"


# Convenience function for backward compatibility
def get_ai_service(logger: Optional[logging.Logger] = None) -> AIService:
    """
    Get an instance of AIService.
    
    Args:
        logger: Optional logger instance
        
    Returns:
        AIService instance
    """
    return AIService(logger)

