from importlib import metadata
from . import algorithms, fasta
from ._file import checksum_file

__all__ = [
    # props
    "__version__",

    # submodules
    "algorithms",
    "fasta",

    # module methods
    "checksum_file",
]

__version__ = metadata.version(__name__)
