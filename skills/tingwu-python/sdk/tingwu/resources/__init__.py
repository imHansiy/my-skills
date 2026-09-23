"""业务资源模块。"""

from __future__ import annotations

from .account import AccountResource
from .directory import DirectoryResource
from .lab import LabResource
from .export import ExportResource
from .notice import NoticeResource
from .share import ShareResource
from .subscription import SubscriptionResource
from .trans import TransResource
from .trash import TrashResource
from .collect import CollectResource
from .discover import DiscoverResource
from .meeting import MeetingResource

__all__ = [
    "AccountResource",
    "DirectoryResource",
    "ExportResource",
    "LabResource",
    "NoticeResource",
    "ShareResource",
    "SubscriptionResource",
    "TransResource",
    "TrashResource",
    "CollectResource",
    "DiscoverResource",
    "MeetingResource",
]
