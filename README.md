# fasta-checksum-utils

Asynchronous library and command-line utility for checksumming FASTA files and individual contigs.


## Installation

To install `fasta-checksum-utils`, run the following `pip` command:

```bash
pip install fasta-checksum-utils
```


## CLI Usage

To generate a text report of checksums in the FASTA document, run the following command:

```bash
fasta-checksum-utils ./my-fasta.fa[.gz]
```

This will print output in the following tab-delimited format:

```
file  [file size in bytes]    MD5 [file MD5 hash]           TRUNC512  [file TRUNC512 hash]
chr1  [chr1 sequence length]  MD5 [chr1 sequence MD5 hash]  TRUNC512  [chr1 sequence TRUNC512 hash]
chr2  [chr2 sequence length]  MD5 [chr2 sequence MD5 hash]  TRUNC512  [chr2 sequence TRUNC512 hash]
...
```

The following example is the output generated by specifying the SARS-CoV-2 genome FASTA from NCBI:

```
file        30429  MD5  863ee5dba1da0ca3f87783782284d489  TRUNC512  3036e94352072c8cd4b5d2e855a72af3d4ca010f6fac1353
NC_045512.2 29903  MD5  105c82802b67521950854a851fc6eefd  TRUNC512  4b2195260fd845e771bec8e9a8d754832caac7b9547eefc3
```

If the `--out-format bento-json` arguments are passed, the tool will instead output the report in a JSON
format, designed to be compatible with the requirements of the 
[Bento Reference Service](https://github.com/bento-platform/bento_reference_service). The following example
is the output generated by specifying the SARS-CoV-2 genome:

```json
{
  "md5": "863ee5dba1da0ca3f87783782284d489",
  "trunc512": "3036e94352072c8cd4b5d2e855a72af3d4ca010f6fac1353",
  "fasta_size": 30429,
  "contigs": [
    {
      "name": "NC_045512.2",
      "md5": "105c82802b67521950854a851fc6eefd",
      "trunc512": "4b2195260fd845e771bec8e9a8d754832caac7b9547eefc3",
      "length": 29903
    }
  ]
}
```

If an argument like `--genome-id GRCh38` is provided, an additional `"id": "GRCh38"` property will be added to the
JSON object output.


## Library Usage

Below are some examples of how `fasta-checksum-utils` can be used as an asynchronous Python library:

```python
import asyncio
import fasta_checksum_utils as fc
import pysam
from pathlib import Path


async def demo():
    covid_genome: Path = Path("./sars_cov_2.fa")
    
    # calculate an MD5 checksum for a whole file
    file_checksum: str = await fc.algorithms.AlgorithmMD5.checksum_file(covid_genome)
    print(file_checksum)
    # prints "863ee5dba1da0ca3f87783782284d489"
    
    all_algorithms = (fc.algorithms.AlgorithmMD5, fc.algorithms.AlgorithmTRUNC512)
    
    # calculate multiple checksums for a whole file
    all_checksums: tuple[str, ...] = await fc.checksum_file(file=covid_genome, algorithms=all_algorithms)
    print(all_checksums)
    # prints tuple: ("863ee5dba1da0ca3f87783782284d489", "3036e94352072c8cd4b5d2e855a72af3d4ca010f6fac1353")
    
    # calculate an MD5 and TRUNC512 checksum for a specific contig in a PySAM FASTA file:
    fh = pysam.FastaFile(str(covid_genome))
    try:
        contig_checksums: tuple[str, ...] = await fc.checksum_contig(
            fh=fh, 
            contig_name="NC_045512.2", 
            algorithms=all_algorithms,
        )
        print(contig_checksums)
        # prints tuple: ("105c82802b67521950854a851fc6eefd", "4b2195260fd845e771bec8e9a8d754832caac7b9547eefc3")
    finally:
        fh.close()  # always close the file handle


asyncio.run(demo())
```
