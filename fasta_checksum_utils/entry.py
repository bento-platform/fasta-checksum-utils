import argparse
import asyncio

from . import __version__
from .algorithms import AlgorithmMD5, AlgorithmGA4GH
from .fasta import fasta_report


async def main():
    parser = argparse.ArgumentParser(
        prog="fasta-checksum-utils",
        description="A library and command-line utility for checksumming FASTA files and individual contigs.",
    )

    parser.add_argument('--version', action="version", version=__version__)

    parser.add_argument("fasta", type=str, help="A FASTA path or URI to checksum.")
    parser.add_argument("--fai", type=str, help="A FASTA FAI index path or URI, if available.")
    parser.add_argument("--genome-id", type=str, help="Genome ID to include, if --out-format is set to bento-json.")
    parser.add_argument("--circular-contigs", type=str, nargs="*", help="Names of circular contigs in this genome.")
    parser.add_argument(
        "--out-format", type=str, default="text", choices=("text", "bento-json"),
        help="Output format for checksum report; either 'text' or 'bento-json' (default: 'text').")

    args = parser.parse_args()

    report = await fasta_report(args.fasta, args.fai, frozenset(args.circular_contigs), (AlgorithmMD5, AlgorithmGA4GH))
    if args.out_format == "bento-json":
        print(report.as_bento_json(genome_id=getattr(args, "genome_id", None)))
    else:
        print(report.as_text_report(), end="")


def entry():
    asyncio.run(main())


if __name__ == "__main__":  # pragma: no cover
    entry()
