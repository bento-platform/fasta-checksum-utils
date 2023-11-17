#!/usr/bin/env bash
poetry run pytest -svv --cov=fasta_checksum_utils --cov-branch
poetry run coverage html
