"""Base notifier interface"""
from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """通知渠道基类"""

    @abstractmethod
    def send(self, title, content, content_type="markdown"):
        pass