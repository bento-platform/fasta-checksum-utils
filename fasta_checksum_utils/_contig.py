import pysam
from typing import Generator, Tuple
from .algorithms import ChecksumAlgorithm


__all__ = [
    "SEQUENCE_CHUNK_SIZE",
    "checksum_contig",
]


SEQUENCE_CHUNK_SIZE = 128 * 1024  # 128 KB of bases at a time


async def checksum_contig(fh: pysam.FastaFile, contig_name: str, algorithms: Tuple[ChecksumAlgorithm, ...]):
    contig_length = fh.get_reference_length(contig_name)

    def gen_sequence() -> Generator[bytes, None, None]:
        for offset in range(0, contig_length, SEQUENCE_CHUNK_SIZE):
            yield (
                fh
                .fetch(contig_name, offset, min(offset + SEQUENCE_CHUNK_SIZE, contig_length))
                .encode("ascii")
            )

    r = []
    for a in algorithms:
        r.append(await a.checksum_sequence(gen_sequence()))

    return tuple(r)
