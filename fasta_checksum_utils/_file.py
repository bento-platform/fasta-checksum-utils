import asyncio
from pathlib import Path
from typing import Tuple
from .algorithms import ChecksumAlgorithm


async def checksum_file(file: Path, algorithms: Tuple[ChecksumAlgorithm, ...]) -> tuple[str, ...]:
    return tuple(await asyncio.gather(*(a.checksum_file(file) for a in algorithms)))
