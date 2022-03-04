import re

RE_NCBI_ACCESSION = re.compile(r'^((?:GCA|GCF)_[\d]{9}\.\d)$')


def is_ncbi_accession(accession: str) -> bool:
    """Validates that the accession is a valid NCBI accession."""
    return bool(re.match(RE_NCBI_ACCESSION, accession))
