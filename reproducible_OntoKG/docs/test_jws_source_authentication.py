"""Integrity checks, not independent repetition of manual source review."""
import json, unittest
from pathlib import Path, PureWindowsPath
from docs.jws_source_authentication import OUT, REVIEWED_HASHES, sha

class SourceAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads((OUT/'results.json').read_text(encoding='utf-8'))
    def test_bounded_counts(self):
        self.assertEqual(len(self.r['sources']),4)
        self.assertEqual(sum(self.r['status_counts'].values()),16)
        self.assertEqual(self.r['status_counts']['registered_source_period_mismatch'],6)
    def test_inspected_copy_integrity(self):
        for source in self.r['sources']:
            self.assertEqual(source['sha256'],REVIEWED_HASHES[source['company']])
            self.assertEqual(sha(OUT/'evidence'/PureWindowsPath(source['file']).name),source['sha256'])
    def test_no_wrong_unit_is_exact_match(self):
        for f in self.r['facts']:
            if f['status']=='exact_value_and_unit_match':
                self.assertTrue(f['raw_unit_correct'])
            if f['status']=='registered_source_period_mismatch':
                self.assertNotIn('normalization_multiplier',f)
            self.assertTrue(f['original_preserved'])
if __name__=='__main__':unittest.main()
