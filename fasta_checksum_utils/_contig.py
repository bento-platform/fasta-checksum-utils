import asyncio
import pysam
from typing import Generator
from .algorithms import ChecksumAlgorithm


__all__ = [
    "SEQUENCE_CHUNK_SIZE",
    "checksum_contig",
]


SEQUENCE_CHUNK_SIZE = 128 * 1024  # 128 KB of bases at a time


async def checksum_contig(fh: pysam.FastaFile, contig_name: str, algorithms: tuple[ChecksumAlgorithm, ...]):
    contig_length = fh.get_reference_length(contig_name)

    def gen_sequence() -> Generator[bytes, None, None]:
        for offset in range(0, contig_length, SEQUENCE_CHUNK_SIZE):
            yield (
                fh
                .fetch(contig_name, offset, min(offset + SEQUENCE_CHUNK_SIZE, contig_length))
                .upper()  # See http://samtools.github.io/hts-specs/refget.html#checksum-calculation
                .encode("ascii")
            )

    return tuple(await asyncio.gather(*(a.checksum_sequence(gen_sequence()) for a in algorithms)))
