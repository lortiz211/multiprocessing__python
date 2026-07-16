"""
This is a module to look at the creation of abstract classes
"""

import abc


class MediaLoader(abc.ABC):
    ext: str

    @abc.abstractmethod
    def play(self) -> None: ...


class Wav(MediaLoader):
    pass


class Ogg(MediaLoader):
    ext = ".ogg"

    def play(self) -> None:
        pass
