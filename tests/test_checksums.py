import json
import pathlib
import pysam
import pytest
from fasta_checksum_utils import checksum_file, checksum_contig
from fasta_checksum_utils.algorithms import AlgorithmMD5, AlgorithmGA4GH
from fasta_checksum_utils.fasta import fasta_report


EXAMPLE_FASTA = pathlib.Path(__file__).parent / "data" / "example.fa"
EXAMPLE_FAI = pathlib.Path(__file__).parent / "data" / "example.fa.fai"

REF_MITO_URL = "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chrM.fa.gz"

TESTED_ALGORITHMS = (AlgorithmMD5, AlgorithmGA4GH)


@pytest.mark.asyncio
async def test_file_checksums():
    assert (await checksum_file(EXAMPLE_FASTA, TESTED_ALGORITHMS)) == (
        "3cc31e8136477d1c7d7e2b7c050c06bd",
        "SQ.6bmN3XulzDYiGZpTXsMkSFQgErtuFD3x",
    )


@pytest.mark.asyncio
async def test_contig_checksums():
    fh = pysam.FastaFile(str(EXAMPLE_FASTA))  # TODO: proper resource
    try:
        assert (await checksum_contig(fh, "chr1", TESTED_ALGORITHMS)) == (
            "bd6a33a85050db787b28c0c8230aaa80",
            "SQ.oTteVImewK0_Z6cUA2c7QUb5YaAq8Hg9",
        )
    finally:
        fh.close()


@pytest.mark.asyncio
async def test_fasta_report():
    report = await fasta_report(EXAMPLE_FASTA, EXAMPLE_FAI, TESTED_ALGORITHMS)

    text_report = report.as_text_report()  # just make sure this doesn't break
    text_report_lines = text_report.split("\n")
    assert len(text_report_lines) == 4  # file + 2 contigs + trailing line

    json_report = report.as_bento_json(genome_id="hello")
    json_data = json.loads(json_report)

    assert json_data["id"] == "hello"

    assert json_data["fasta"] == str(EXAMPLE_FASTA)
    assert json_data["fai"] == str(EXAMPLE_FAI)

    # file checksums
    assert json_data["md5"] == "3cc31e8136477d1c7d7e2b7c050c06bd"
    assert json_data["ga4gh"] == "SQ.6bmN3XulzDYiGZpTXsMkSFQgErtuFD3x"

    # contigs
    assert len(json_data["contigs"]) == 2
    assert json_data["contigs"][0]["md5"] == "bd6a33a85050db787b28c0c8230aaa80"
    assert json_data["contigs"][0]["ga4gh"] == "SQ.oTteVImewK0_Z6cUA2c7QUb5YaAq8Hg9"
    assert json_data["contigs"][0]["length"] == 33
    assert json_data["contigs"][1]["length"] == 28


@pytest.mark.asyncio
async def test_fasta_report_http():
    report = await fasta_report(REF_MITO_URL, None, TESTED_ALGORITHMS)

    text_report = report.as_text_report()  # just make sure this doesn't break
    text_report_lines = text_report.split("\n")
    assert len(text_report_lines) == 3  # file + 1 contig + trailing line
