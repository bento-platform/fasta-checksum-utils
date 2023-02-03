import json
import pysam
from pathlib import Path
from typing import Dict, Tuple, Union

from .algorithms import ChecksumAlgorithm
from ._contig import checksum_contig
from ._file import checksum_file


class FastaReport:

    def __init__(
        self,
        file_checksums: Dict[ChecksumAlgorithm, str],
        file_size: int,
        sequence_checksums_and_lengths: Dict[str, Tuple[Dict[ChecksumAlgorithm, str], int]],
    ):
        self._file_checksums = file_checksums
        self._file_size: int = file_size
        self._sequence_checksums_and_lengths = sequence_checksums_and_lengths

    def as_bento_json(self, genome_id: Union[str, None] = None) -> str:
        def _checksum_dict(cs: Dict[ChecksumAlgorithm, str]) -> Dict[str, str]:
            return {str(algorithm).lower(): checksum for algorithm, checksum in cs.items()}

        return json.dumps({
            **({"id": genome_id} if genome_id else {}),
            **_checksum_dict(self._file_checksums),
            "fasta_size": self._file_size,
            "contigs": [
                {
                    "name": contig,
                    **_checksum_dict(checksums),
                    "length": length
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


async def fasta_report(file: Path, algorithms: Tuple[ChecksumAlgorithm, ...]) -> FastaReport:
    file_size = file.stat().st_size

    # Calculate whole-file checksums

    fcs = await checksum_file(file, algorithms)
    file_checksums = {algorithms[i]: fcs[i] for i in range(len(algorithms))}

    # Calculate sequence content checksums

    fh = pysam.FastaFile(str(file))
    sequence_checksums_and_lengths: Dict[str, Tuple[Dict[ChecksumAlgorithm, str], int]] = {}

    try:
        for sequence_name in fh.references:
            sequence_checksums_and_lengths[sequence_name] = (
                {a: c for a, c in zip(
                    algorithms,
                    await checksum_contig(fh, sequence_name, algorithms),
                )},
                fh.get_reference_length(sequence_name),
            )

    finally:
        fh.close()

    # Generate and return a final report
    return FastaReport(file_checksums, file_size, sequence_checksums_and_lengths)
