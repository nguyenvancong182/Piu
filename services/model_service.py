"""
Model Service for Piu Application

This service handles Whisper model management, loading, transcription, and CUDA/device detection.
Business logic extracted from Piu.py to improve maintainability and testability.

Migration from Piu.py:
- Whisper model loading/unloading
- Device selection (CUDA/CPU)
- Transcription logic
- CUDA availability checking
- VRAM measurement
"""

import logging
import os
import sys
import gc
import subprocess
from typing import Optional, Dict, Tuple, Callable
from contextlib import redirect_stdout, redirect_stderr

# Optional imports with fallback
try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    whisper = None
    logging.warning("Thư viện whisper chưa được cài đặt. Chức năng transcription sẽ không hoạt động.")

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch = None
    logging.warning("Thư viện torch chưa được cài đặt. CUDA detection sẽ bị hạn chế.")

# Import utilities
try:
    from utils.system_utils import is_cuda_available
except ImportError:
    def is_cuda_available():
        """Fallback if system_utils not available"""
        return ("UNKNOWN", 0)

try:
    from config.constants import WHISPER_VRAM_REQ_MB
except ImportError:
    # Fallback VRAM requirements
    WHISPER_VRAM_REQ_MB = {
        "tiny": 1024, "base": 1024, "small": 2048, "medium": 5120,
        "large-v1": 10240, "large-v2": 10240, "large-v3": 10240, "large": 10240,
    }

try:
    from utils.srt_utils import write_srt, write_vtt
except ImportError:
    # Fallback functions if not available
    def write_srt(f, segments):
        """Fallback SRT writer"""
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{seg['start']:.2f} --> {seg['end']:.2f}\n")
            f.write(f"{seg.get('text', '')}\n\n")
    
    def write_vtt(f, segments):
        """Fallback VTT writer"""
        f.write("WEBVTT\n\n")
        for seg in segments:
            f.write(f"{seg['start']:.2f} --> {seg['end']:.2f}\n")
            f.write(f"{seg.get('text', '')}\n\n")

# Constants
APP_NAME = "Piu"


class ModelService:
    """
    Service for Whisper model management, loading, and transcription.
    
    This service contains all business logic for Whisper model operations,
    separate from UI handling which remains in Piu.py.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize Model Service.
        
        Args:
            logger: Optional logger instance. If None, creates a new logger.
        """
        self.logger = logger or logging.getLogger(APP_NAME)
        self.logger.info("[ModelService] Initializing Model Service...")
        
        # Model state
        self.current_model = None
        self.model_name = None
        self.device = None
        
        # CUDA state
        self.cuda_status = "UNKNOWN"
        self.gpu_vram_mb = 0
        
        # Loading flag
        self.is_loading_model = False
        
        # Initialize CUDA status
        self._check_cuda_status()
    
    def _check_cuda_status(self):
        """Check CUDA status on initialization."""
        try:
            status, vram_mb = is_cuda_available()
            self.cuda_status = status
            self.gpu_vram_mb = vram_mb
            self.logger.info(f"[ModelService] CUDA status: {status}, VRAM: {vram_mb} MB")
        except Exception as e:
            self.logger.warning(f"[ModelService] Error checking CUDA status: {e}")
            self.cuda_status = "UNKNOWN"
            self.gpu_vram_mb = 0
    
    # ========================================================================
    # CUDA/DEVICE METHODS
    # ========================================================================
    
    def check_cuda_availability(self) -> Tuple[str, int]:
        """
        Check CUDA/GPU availability and VRAM.
        
        Returns:
            Tuple of (status, vram_mb)
            - status: 'AVAILABLE', 'NO_DEVICE', 'COMMAND_NOT_FOUND', 'ERROR', or 'UNKNOWN'
            - vram_mb: VRAM in MB (0 if unavailable)
        """
        try:
            status, vram_mb = is_cuda_available()
            self.cuda_status = status
            self.gpu_vram_mb = vram_mb
            self.logger.info(f"[ModelService] CUDA check: {status}, VRAM: {vram_mb} MB")
            return status, vram_mb
        except subprocess.TimeoutExpired:
            self.logger.warning("[ModelService] CUDA check timeout - nvidia-smi mất quá nhiều thời gian")
            self.cuda_status = "ERROR"
            self.gpu_vram_mb = 0
            return "ERROR", 0
        except Exception as e:
            self.logger.error(f"[ModelService] Error checking CUDA: {e}", exc_info=True)
            self.cuda_status = "ERROR"
            self.gpu_vram_mb = 0
            return "ERROR", 0
    
    def get_recommended_device(self, model_name: str) -> str:
        """
        Get recommended device (cuda/cpu) for a given model.
        
        Args:
            model_name: Whisper model name (e.g., "base", "large")
            
        Returns:
            Recommended device: "cuda" or "cpu"
        """
        try:
            # Check if PyTorch sees CUDA
            if HAS_TORCH and torch is not None:
                if not torch.cuda.is_available():
                    self.logger.warning("torch.cuda.is_available() is False. Using CPU.")
                    return "cpu"
            else:
                self.logger.debug("PyTorch not available. Using CPU.")
                return "cpu"
            
            # If PyTorch sees CUDA, check VRAM requirements
            if self.cuda_status != 'AVAILABLE':
                self.logger.debug("CUDA status is not AVAILABLE. Using CPU.")
                return "cpu"
            
            # Check VRAM requirements
            required_vram = WHISPER_VRAM_REQ_MB.get(model_name, 0)
            
            if self.gpu_vram_mb > 0 and required_vram > 0:
                if self.gpu_vram_mb < required_vram:
                    self.logger.warning(
                        f"GPU VRAM ({self.gpu_vram_mb / 1024:.1f}GB) insufficient for model '{model_name}' "
                        f"(~{required_vram / 1024:.1f}GB). Using CPU."
                    )
                    return "cpu"
                else:
                    self.logger.debug(
                        f"Using CUDA (VRAM sufficient: {self.gpu_vram_mb}MB >= {required_vram}MB)"
                    )
                    return "cuda"
            else:
                self.logger.debug("Using CUDA (no VRAM info or model has no requirement)")
                return "cuda"
                
        except ImportError:
            self.logger.error("Cannot import torch. Using CPU.")
            return "cpu"
        except Exception as e:
            self.logger.error(f"Error determining device: {e}. Using CPU.", exc_info=True)
            return "cpu"
    
    # ========================================================================
    # MODEL LOADING METHODS
    # ========================================================================
    
    def load_model(
        self,
        model_name: str,
        device: Optional[str] = None,
        force_reload: bool = False,
        stop_event: Optional[Callable[[], bool]] = None
    ) -> Tuple[Optional[object], Optional[str], Optional[str], Optional[str]]:
        """
        Load Whisper model.
        
        Args:
            model_name: Whisper model name to load
            device: Target device ("cuda" or "cpu"). If None, auto-determines.
            force_reload: Force reload even if same model is already loaded
            stop_event: Callable that returns True if loading should stop
            
        Returns:
            Tuple of (model_object, model_name, device, error_message)
            - model_object: Loaded Whisper model, or None on error
            - model_name: Model name that was loaded
            - device: Device used ("cuda" or "cpu")
            - error_message: Error message string, or None on success
        """
        log_prefix = f"[ModelService:Load]"
        
        if not HAS_WHISPER or whisper is None:
            error_msg = "Thư viện Whisper chưa được cài đặt."
            self.logger.error(f"{log_prefix} {error_msg}")
            return None, None, None, error_msg
        
        # Check if already loaded and matches
        if not force_reload and self.current_model is not None:
            if self.model_name == model_name and self.device == device:
                self.logger.info(f"{log_prefix} Model '{model_name}' on '{device}' already loaded.")
                return self.current_model, self.model_name, self.device, None
        
        # Determine device if not provided
        if device is None:
            device = self.get_recommended_device(model_name)
        
        # Check stop event
        if stop_event and stop_event():
            return None, None, None, "Đã dừng bởi người dùng."
        
        # Unload old model
        self.unload_model()
        
        # Check stop event again
        if stop_event and stop_event():
            return None, None, None, "Đã dừng bởi người dùng."
        
        try:
            self.logger.info(f"{log_prefix} Loading model '{model_name}' on device '{device}'...")
            
            # Disable tqdm progress bar
            old_tqdm_disable = os.environ.get("TQDM_DISABLE", None)
            
            # Load model with output redirection
            with open(os.devnull, "w", encoding="utf-8") as fnull:
                orig_stderr = sys.stderr
                patched_stderr = False
                if orig_stderr is None:
                    sys.stderr = fnull
                    patched_stderr = True
                
                try:
                    os.environ["TQDM_DISABLE"] = "1"
                    
                    # Try loading with fallback CUDA -> CPU
                    try:
                        with redirect_stdout(fnull), redirect_stderr(fnull):
                            loaded_model = whisper.load_model(model_name, device=device)
                    except Exception as e1:
                        if device.lower() == 'cuda':
                            self.logger.warning(f"{log_prefix} CUDA load failed: {e1}. Fallback to CPU...")
                            try:
                                with redirect_stdout(fnull), redirect_stderr(fnull):
                                    loaded_model = whisper.load_model(model_name, device="cpu")
                                device = "cpu"  # Update actual device used
                            except Exception as e2:
                                error_msg = f"CUDA error: {e1}; CPU fallback error: {e2}"
                                self.logger.error(f"{log_prefix} {error_msg}", exc_info=True)
                                return None, None, None, error_msg
                        else:
                            raise
                    
                finally:
                    # Restore environment
                    if old_tqdm_disable is None:
                        os.environ.pop("TQDM_DISABLE", None)
                    else:
                        os.environ["TQDM_DISABLE"] = old_tqdm_disable
                    
                    # Restore stderr
                    if patched_stderr:
                        sys.stderr = orig_stderr
            
            # Success - update state
            self.current_model = loaded_model
            self.model_name = model_name
            self.device = device
            
            self.logger.info(f"{log_prefix} Successfully loaded model '{model_name}' on '{device}'.")
            return loaded_model, model_name, device, None
            
        except ImportError as e:
            error_msg = f"Lỗi import thư viện whisper: {e}"
            self.logger.error(f"{log_prefix} {error_msg}")
            return None, None, None, error_msg
        except Exception as e:
            error_msg = f"Lỗi tải model '{model_name}' lên '{device}': {e}"
            self.logger.error(f"{log_prefix} {error_msg}", exc_info=True)
            return None, None, None, error_msg
    
    def unload_model(self):
        """Unload current Whisper model and free memory."""
        if self.current_model is not None:
            self.logger.debug("[ModelService] Unloading current model...")
            del self.current_model
            self.current_model = None
            gc.collect()
            
            # Clear CUDA cache if available
            if self.device == "cuda" and HAS_TORCH and torch is not None:
                try:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        self.logger.debug("[ModelService] Cleared CUDA cache.")
                except Exception:
                    pass
            
            self.model_name = None
            self.device = None
            self.logger.debug("[ModelService] Model unloaded.")
    
    def is_model_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self.current_model is not None
    
    def get_model_info(self) -> Dict[str, Optional[str]]:
        """
        Get current model information.
        
        Returns:
            Dict with keys: 'model_name', 'device', 'cuda_status', 'vram_mb'
        """
        return {
            'model_name': self.model_name,
            'device': self.device,
            'cuda_status': self.cuda_status,
            'vram_mb': self.gpu_vram_mb
        }
    
    # ========================================================================
    # TRANSCRIPTION METHODS
    # ========================================================================
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        fp16: Optional[bool] = None,
        **kwargs
    ) -> Dict:
        """
        Transcribe audio file using current loaded model.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., "vi", "en", "auto"). If None, auto-detects.
            fp16: Use FP16 precision (faster on CUDA). If None, auto-detects based on device.
            **kwargs: Additional transcribe options
            
        Returns:
            Transcription result dictionary with 'text' and 'segments'
            
        Raises:
            RuntimeError: If model is not loaded or other transcription error
        """
        log_prefix = "[ModelService:Transcribe]"
        
        if self.current_model is None:
            raise RuntimeError("Model chưa được load. Vui lòng load model trước khi transcribe.")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file không tồn tại: {audio_path}")
        
        # Determine FP16 based on device if not specified
        if fp16 is None:
            fp16 = (self.device == 'cuda')
        
        # Build transcribe options
        transcribe_options = {
            'fp16': fp16,
            'patience': 2.0,
            'beam_size': 5,
            'no_speech_threshold': 0.45,
            'logprob_threshold': -0.8,
            **kwargs
        }
        
        if language and language != "auto":
            transcribe_options['language'] = language
        
        try:
            self.logger.info(
                f"{log_prefix} Transcribing '{os.path.basename(audio_path)}' "
                f"(Model: '{self.model_name}', Device: {self.device}, FP16: {fp16}, Lang: {language or 'auto'})"
            )
            
            result = self.current_model.transcribe(audio_path, **transcribe_options)
            
            num_segments = len(result.get('segments', []))
            self.logger.info(f"{log_prefix} Transcription complete. Found {num_segments} segments.")
            
            return result
            
        except Exception as e:
            self.logger.error(
                f"{log_prefix} Error transcribing on device '{self.device}': {e}",
                exc_info=True
            )
            raise
    
    def transcribe_and_save(
        self,
        audio_path: str,
        output_path: str,
        output_format: str = "srt",
        language: Optional[str] = None,
        fp16: Optional[bool] = None,
        **kwargs
    ) -> str:
        """
        Transcribe audio file and save to output file.
        
        Args:
            audio_path: Path to audio file
            output_path: Path to save output file
            output_format: Output format ("txt", "srt", or "vtt")
            language: Language code
            fp16: Use FP16 precision
            **kwargs: Additional transcribe options
            
        Returns:
            Path to saved output file
            
        Raises:
            RuntimeError: If model is not loaded or transcription fails
            ValueError: If output_format is not supported
        """
        # Transcribe
        result = self.transcribe(audio_path, language=language, fp16=fp16, **kwargs)
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Write output file
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                if output_format == 'txt':
                    f.write(result["text"])
                elif output_format == 'srt':
                    write_srt(f, result['segments'])
                elif output_format == 'vtt':
                    write_vtt(f, result['segments'])
                else:
                    self.logger.warning(
                        f"Output format '{output_format}' not supported. Saving as TXT."
                    )
                    f.write(result["text"])
            
            self.logger.info(f"[ModelService] Saved transcription to: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(
                f"[ModelService] Error saving transcription to '{output_path}': {e}",
                exc_info=True
            )
            raise

