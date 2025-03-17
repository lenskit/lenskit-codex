"""
Data split abstraction.
"""

from abc import ABC, abstractmethod

from lenskit.splitting import TTSplit


class SplitSet(ABC):
    """
    Base class for splits of data.
    """

    parts: list[str]

    @abstractmethod
    def get_part(self, split: str) -> TTSplit: ...
