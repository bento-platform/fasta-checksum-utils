import json
import pathlib
import pysam
import pytest
from fasta_checksum_utils import checksum_file, checksum_contig
from fasta_checksum_utils.algorithms import AlgorithmMD5, AlgorithmTRUNC512
from fasta_checksum_utils.fasta import fasta_report


EXAMPLE_FASTA = pathlib.Path(__file__).parent / "data" / "example.fa"
TESTED_ALGORITHMS = (AlgorithmMD5, AlgorithmTRUNC512)


@pytest.mark.asyncio
async def test_file_checksums():
    assert (await checksum_file(EXAMPLE_FASTA, TESTED_ALGORITHMS)) == (
        "3cc31e8136477d1c7d7e2b7c050c06bd",
        "e9b98ddd7ba5cc3622199a535ec32448542012bb6e143df1",
    )


@pytest.mark.asyncio
async def test_contig_checksums():
    fh = pysam.FastaFile(str(EXAMPLE_FASTA))  # TODO: proper resource
    try:
        assert (await checksum_contig(fh, "chr1", TESTED_ALGORITHMS)) == (
            "bd6a33a85050db787b28c0c8230aaa80",
            "a13b5e54899ec0ad3f67a71403673b4146f961a02af0783d",
        )
    finally:
        fh.close()


@pytest.mark.asyncio
async def test_fasta_report():
    report = await fasta_report(EXAMPLE_FASTA, TESTED_ALGORITHMS)

    text_report = report.as_text_report()  # just make sure this doesn't work
    text_report_lines = text_report.split("\n")
    assert len(text_report_lines) == 4  # file + 2 contigs + trailing line

    json_report = report.as_bento_json(genome_id="hello")
    assert json.loads(json_report)["id"] == "hello"

    json_report = report.as_bento_json()
    json_data = json.loads(json_report)

    # file checksums
    assert json_data["md5"] == "3cc31e8136477d1c7d7e2b7c050c06bd"
    assert json_data["trunc512"] == "e9b98ddd7ba5cc3622199a535ec32448542012bb6e143df1"

    # contigs
    assert len(json_data["contigs"]) == 2
    assert json_data["contigs"][0]["md5"] == "bd6a33a85050db787b28c0c8230aaa80"
    assert json_data["contigs"][0]["trunc512"] == "a13b5e54899ec0ad3f67a71403673b4146f961a02af0783d"
    assert json_data["contigs"][0]["length"] == 33
    assert json_data["contigs"][1]["length"] == 28
