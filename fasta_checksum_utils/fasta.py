import aiofiles
import aiohttp
import asyncio
import json
import os
import pysam
import tempfile

from pathlib import Path
from typing import Union

from .algorithms import ChecksumAlgorithm
from ._contig import checksum_contig
from ._file import checksum_file


DOWNLOAD_CHUNK_SIZE = 128 * 1024  # 128 KB


class FastaReport:

    def __init__(
        self,
        fasta_path_or_uri: str,
        fai_path_or_uri: Union[str, None],
        file_checksums: dict[ChecksumAlgorithm, str],
        file_size: int,
        sequence_checksums_and_lengths: dict[str, tuple[dict[ChecksumAlgorithm, str], int]],
        circular_contigs: frozenset[str],
    ):
        self._fasta_path_or_uri: str = fasta_path_or_uri
        self._fai_path_or_uri: Union[str, None] = fai_path_or_uri
        self._file_checksums = file_checksums
        self._file_size: int = file_size
        self._sequence_checksums_and_lengths = sequence_checksums_and_lengths
        self._circular_contigs: frozenset[str] = circular_contigs

    @property
    def fasta_path_or_uri(self) -> str:
        return self._fasta_path_or_uri

    @property
    def fai_path_or_uri(self) -> Union[str, None]:
        return self._fai_path_or_uri

    def as_bento_json(self, genome_id: Union[str, None] = None) -> str:
        def _checksum_dict(cs: dict[ChecksumAlgorithm, str]) -> dict[str, str]:
            return {str(algorithm).lower(): checksum for algorithm, checksum in cs.items()}

        return json.dumps({
            **({"id": genome_id} if genome_id else {}),
            "fasta": self.fasta_path_or_uri,
            "fasta_size": self._file_size,
            **({"fai": self.fai_path_or_uri} if self.fai_path_or_uri else {}),
            **_checksum_dict(self._file_checksums),
            "contigs": [
                {
                    "name": contig,
                    "aliases": [],
                    **_checksum_dict(checksums),
                    "length": length,
                    "circular": contig in self._circular_contigs,
                }
                for contig, (checksums, length) in self._sequence_checksums_and_lengths.items()
            ]
        }, indent=2)

    def as_text_report(self) -> str:
        text_report = ""

        text_report += f"file\t{self._file_size}"
        for algorithm, checksum in self._file_checksums.items():
            text_report += f"\t{algorithm}\t{checksum}"
        text_report += "\n"

        for sequence_name, (checksums, length) in self._sequence_checksums_and_lengths.items():
            text_report += f"{sequence_name}\t{length}"
            for algorithm, checksum in checksums.items():
                text_report += f"\t{algorithm}\t{checksum}"
            text_report += "\n"

        return text_report


async def _get_fasta_sequence_checksums_and_lengths(
    fh: pysam.FastaFile,
    algorithms: tuple[ChecksumAlgorithm, ...],
) -> dict[str, tuple[dict[ChecksumAlgorithm, str], int]]:
    sequence_checksums_and_lengths: dict[str, tuple[dict[ChecksumAlgorithm, str], int]] = {}

    for sequence_name in fh.references:
        sequence_checksums_and_lengths[sequence_name] = (
            {a: c for a, c in zip(
                algorithms,
                await checksum_contig(fh, sequence_name, algorithms),
            )},
            fh.get_reference_length(sequence_name),
        )

    return sequence_checksums_and_lengths


def _is_http_url(x: str) -> bool:
    return x.startswith("http://") or x.startswith("https://")


async def fasta_report(
    fasta_path_or_uri: Union[Path, str],
    fai_path_or_uri: Union[Path, str, None],
    circular_contigs: frozenset[str],
    algorithms: tuple[ChecksumAlgorithm, ...],
) -> FastaReport:
    tmp_file_fa = None
    tmp_file_fai = None

    try:
        # Obtain fasta_path_or_uri size:
        #  - if it's on the local fasta_path_or_uri system, use stat()
        #  - otherwise, use a HEAD response Content-Length header

        if isinstance(fasta_path_or_uri, Path) or not _is_http_url(fasta_path_or_uri):
            file_size = Path(fasta_path_or_uri).stat().st_size
        else:
            tmp_file_fa = tempfile.NamedTemporaryFile(delete=False)
            tmp_file_fai = tempfile.NamedTemporaryFile(delete=False) if fai_path_or_uri else None
            async with aiohttp.ClientSession() as session:
                async with session.head(fasta_path_or_uri, allow_redirects=True) as res:
                    file_size = res.headers["content-length"]

                # Download FASTA file from URL
                async with session.get(fasta_path_or_uri, allow_redirects=True) as res, \
                        aiofiles.open(tmp_file_fa.name, "wb") as tfh:
                    async for data in res.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                        await tfh.write(data)

                # If a FASTA URL is passed, assume if we have a FAI it is also a URL
                if fai_path_or_uri:
                    async with session.get(fai_path_or_uri, allow_redirects=True) as res, \
                            aiofiles.open(tmp_file_fai.name, "wb") as tfh:
                        async for data in res.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                            await tfh.write(data)

                try:
                    pysam.FastaFile(tmp_file_fa.name, filepath_index=tmp_file_fai.name if tmp_file_fai else None)
                except OSError as e:
                    if "error when opening file" not in str(e):  # pragma: no cover
                        raise e

                    # Assuming this is a non-bgzipped FASTA if an OSError occurs with this string
                    with tempfile.NamedTemporaryFile() as tf:
                        p = await asyncio.create_subprocess_exec(
                            "gunzip", "-c", tmp_file_fa.name, stdout=tf)

                        r = await p.wait()
                        if r != 0:  # pragma: no cover
                            raise Exception("Error while gunzipping downloaded FASTA")

                        with open(tmp_file_fa.name, "wb") as tfh:
                            p = await asyncio.create_subprocess_exec("cat", tf.name, stdout=tfh)
                            await p.wait()

        fasta_str = str(fasta_path_or_uri)
        fai_str = str(fai_path_or_uri) if fai_path_or_uri else None

        fasta_true_path = tmp_file_fa.name if tmp_file_fa else fasta_str
        fai_true_path = tmp_file_fai.name if tmp_file_fai else fai_str

        # Calculate whole-fasta_path_or_uri checksums

        fcs = await checksum_file(fasta_true_path, algorithms)
        file_checksums = {algorithms[i]: fcs[i] for i in range(len(algorithms))}

        # Calculate sequence content checksums

        fh = pysam.FastaFile(fasta_true_path, filepath_index=fai_true_path)
        try:
            sequence_checksums_and_lengths: dict[str, tuple[dict[ChecksumAlgorithm, str], int]] = (
                await _get_fasta_sequence_checksums_and_lengths(fh, algorithms))
        finally:
            fh.close()

    finally:
        if tmp_file_fa:
            os.unlink(tmp_file_fa.name)
        if tmp_file_fai:
            os.unlink(tmp_file_fai.name)

    # Generate and return a final report
    return FastaReport(fasta_str, fai_str, file_checksums, file_size, sequence_checksums_and_lengths, circular_contigs)
