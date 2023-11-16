import asyncio
from pathlib import Path
from .algorithms import ChecksumAlgorithm


async def checksum_file(file: Path, algorithms: tuple[ChecksumAlgorithm, ...]) -> tuple[str, ...]:
    return tuple(await asyncio.gather(*(a.checksum_file(file) for a in algorithms)))
