import csv
import gzip
import hashlib
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import split  # noqa: E402

HEADER = ",".join(split.COLUMNS)
ROWS = [
    "GSM,238,1,100,5,0,10.5,55.5,1000,3,1,1600000000,1700000000,0",
    "LTE,238,2,50,9,0,10.6,55.6,500,7,1,1600000000,1700000000,-80",
    "GSM,238,1,100,2,0,10.4,55.4,900,2,1,1600000000,1700000000,0",
    "UMTS,240,1,7,1,0,18.0,59.3,800,4,1,1600000000,1700000000,0",
]
MALFORMED = "GSM,notanumber,1,2,3"


def write_src(path, lines):
    with gzip.open(path, "wt") as fh:
        fh.write("\n".join(lines) + "\n")


def read_gz(path):
    with gzip.open(path, "rt") as fh:
        return fh.read().splitlines()


class SplitTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.dir.name, "in.csv.gz")
        self.out = os.path.join(self.dir.name, "out")

    def tearDown(self):
        self.dir.cleanup()

    def manifest(self):
        with open(os.path.join(self.out, "manifest.json")) as fh:
            return json.load(fh)

    def test_headerless_splits_by_mcc_and_sorts(self):
        write_src(self.src, ROWS)
        stats = split.split(self.src, self.out)
        self.assertEqual(stats, {"rows": 4, "rejected": 0, "files": 2})
        self.assertEqual(read_gz(os.path.join(self.out, "238.csv.gz")),
                         [ROWS[2], ROWS[0], ROWS[1]])
        self.assertEqual(read_gz(os.path.join(self.out, "240.csv.gz")), [ROWS[3]])

    def test_header_row_is_dropped_and_output_has_no_header(self):
        write_src(self.src, [HEADER] + ROWS)
        stats = split.split(self.src, self.out)
        self.assertEqual(stats["rows"], 4)
        self.assertNotIn(HEADER, read_gz(os.path.join(self.out, "238.csv.gz")))

    def test_malformed_rows_are_counted_and_skipped(self):
        write_src(self.src, ROWS + [MALFORMED, ""])
        stats = split.split(self.src, self.out)
        self.assertEqual(stats["rejected"], 1)
        self.assertEqual(stats["rows"], 4)

    def test_manifest_matches_files(self):
        write_src(self.src, ROWS)
        split.split(self.src, self.out)
        m = self.manifest()
        self.assertEqual([f["mcc"] for f in m["files"]], [238, 240])
        for key in ("generatedAt", "source", "licence", "credit"):
            self.assertTrue(m[key])
        for f in m["files"]:
            with open(os.path.join(self.out, f["file"]), "rb") as fh:
                data = fh.read()
            self.assertEqual(f["bytes"], len(data))
            self.assertEqual(f["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(m["files"][0]["rows"], 3)

    def test_output_is_deterministic(self):
        write_src(self.src, ROWS)
        split.split(self.src, self.out)
        first = self.manifest()["files"]
        shuffled = os.path.join(self.dir.name, "s.csv.gz")
        write_src(shuffled, list(reversed(ROWS)))
        split.split(shuffled, self.out)
        self.assertEqual(first, self.manifest()["files"])

    def test_no_temp_files_left_behind(self):
        write_src(self.src, ROWS)
        split.split(self.src, self.out)
        self.assertEqual(sorted(os.listdir(self.out)),
                         ["238.csv.gz", "240.csv.gz", "manifest.json"])

    def test_main_fails_without_valid_rows(self):
        write_src(self.src, [MALFORMED])
        self.assertEqual(split.main(["split.py", self.src, self.out]), 1)


if __name__ == "__main__":
    unittest.main()
