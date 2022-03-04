import unittest

from api.util.ncbi import is_ncbi_accession


class TestNcbi(unittest.TestCase):

    def test_is_ncbi_accession(self):
        true = ['GCA_123456789.1', 'GCF_123456789.2']
        false = ['GB_GCA_123456789.1', 'RS_GCF_123456789.1', 'something', '']

        [self.assertTrue(is_ncbi_accession(x)) for x in true]
        [self.assertFalse(is_ncbi_accession(x)) for x in false]
