from dataclasses import dataclass, field
from enum import Enum
import uuid

__all__ = ["DownloadStatus", "DownloadItem"]


class DownloadStatus(Enum):
    """Status enum for download items, used consistently across the codebase."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadItem:
    """Represents a single download job with URL, folder, filename, and status."""
    url: str
    folder: str
    filename: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: DownloadStatus = DownloadStatus.PENDING
    error_msg: str = ""
