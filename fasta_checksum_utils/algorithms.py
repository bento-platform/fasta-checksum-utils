import aiofiles
import binascii
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator

__all__ = [
    "ChecksumAlgorithm",
    "AlgorithmMD5",
    "AlgorithmTRUNC512",
]

DEFAULT_CHUNK_SIZE = 16 * 1024  # 16 KB
DEFAULT_TRUNC512_OFFSET = 24


class ChecksumAlgorithm(ABC):
    def __init__(self):
        pass

    @staticmethod
    async def update_hash_from_file(h, file: Path, chunk_size: int):
        async with aiofiles.open(file, "rb") as fh:
            while data := fh.read(chunk_size):
                h.update(data)
        return h

    @staticmethod
    def update_hash_from_sequence(h, sequence: Generator[bytes, None, None]):
        while data := next(sequence, None):
            h.update(data)
        return h

    @classmethod
    @abstractmethod
    async def checksum_file(cls, file: Path, chunk_size: int = DEFAULT_CHUNK_SIZE, **kwargs) -> str:
        pass

    @classmethod
    @abstractmethod
    async def checksum_sequence(cls, sequence: Generator[bytes, None, None]) -> str:
        pass


class AlgorithmMD5(ChecksumAlgorithm):
    @classmethod
    async def checksum_file(cls, file: Path, chunk_size: int = DEFAULT_CHUNK_SIZE, **kwargs) -> str:
        return (await cls.update_hash_from_file(hashlib.md5(), file, chunk_size)).hexdigest()

    @classmethod
    async def checksum_sequence(cls, sequence: Generator[bytes, None, None], **kwargs) -> str:
        return cls.update_hash_from_sequence(hashlib.md5(), sequence).hexdigest()


class AlgorithmTRUNC512(ChecksumAlgorithm):
    @staticmethod
    def _trunc512_of_hash(h, offset: int) -> str:
        return binascii.hexlify(h.digest()[:offset]).decode("ascii")

    @classmethod
    async def checksum_file(cls, file: Path, chunk_size: int = DEFAULT_CHUNK_SIZE, **kwargs) -> str:
        return cls._trunc512_of_hash(
            h=await cls.update_hash_from_file(hashlib.sha512(), file, chunk_size),
            offset=kwargs.pop("offset", DEFAULT_CHUNK_SIZE),
        )

    @classmethod
    async def checksum_sequence(cls, sequence: Generator[bytes, None, None], **kwargs) -> str:
        return cls._trunc512_of_hash(
            h=cls.update_hash_from_sequence(hashlib.sha512(), sequence),
            offset=kwargs.pop("offset", DEFAULT_CHUNK_SIZE),
        )
