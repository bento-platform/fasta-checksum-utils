import asyncio
from pathlib import Path
from typing import Union
from .algorithms import ChecksumAlgorithm


async def checksum_file(file: Union[Path, str], algorithms: tuple[ChecksumAlgorithm, ...]) -> tuple[str, ...]:
    return tuple(await asyncio.gather(*(a.checksum_file(file) for a in algorithms)))
