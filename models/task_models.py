from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class DownloadTask:
    """Đại diện một tác vụ tải xuống trong hàng đợi."""
    id: str
    url: str
    output_dir: str
    filename_hint: Optional[str] = None
    status: str = "pending"  # pending | running | done | error | cancelled
    progress: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadTask":
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class DubbingTask:
    """Đại diện một tác vụ thuyết minh/ghép giọng trong hàng đợi."""
    id: str
    identifier: str
    video_path: str
    video_display_name: str
    script_content_type: str  # 'file' | 'textbox' | 'dual_srt'
    script_data: Dict[str, Any]
    tts_engine: str
    voice_id: str
    status: str = "pending"
    progress: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DubbingTask":
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class SubtitleTask:
    """Đại diện một tác vụ phụ đề (tạo/sửa/xử lý)."""
    id: str
    input_video_path: str
    operation: str  # 'transcribe' | 'translate' | 'style' | 'render'
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    progress: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubtitleTask":
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


