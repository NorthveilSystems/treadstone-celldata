#!/usr/bin/env python3
"""Split the OpenCelliD world export into one gzipped headerless CSV per MCC.

Usage: split.py <cell_towers.csv.gz> <out-dir>

The input may or may not start with a header row. Output rows keep the
original 14-column order and are sorted deterministically, so the same input
always yields byte-identical files (gzip mtime is pinned to 0).
"""
import csv
import gzip
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

COLUMNS = ["radio", "mcc", "net", "area", "cell", "unit", "lon", "lat",
           "range", "samples", "changeable", "created", "updated",
           "averageSignal"]
SOURCE = "https://opencellid.org/downloads.php"
LICENCE = "CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)"
CREDIT = ("Cell tower data from OpenCellID (https://opencellid.org), "
          "licensed under CC BY-SA 4.0 "
          "(https://creativecommons.org/licenses/by-sa/4.0/)")


def _int(value):
    if not value.isdigit():
        raise ValueError(value)
    return int(value)


def parse_row(row):
    """Return (mcc, sort_key) or raise ValueError for a malformed row."""
    if len(row) != len(COLUMNS):
        raise ValueError("expected %d columns, got %d" % (len(COLUMNS), len(row)))
    if not row[0]:
        raise ValueError("empty radio")
    mcc = _int(row[1])
    key = (_int(row[2]), _int(row[3]), _int(row[4]), row[0])
    float(row[6])
    float(row[7])
    return mcc, key


def _write_gz(path, write_body):
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0,
                           compresslevel=9) as gz:
            write_body(gz)


def split(src, out_dir, now=None):
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="split-", dir=out_dir)
    handles = {}
    rejected = 0
    total = 0
    try:
        with gzip.open(src, "rt", newline="", encoding="utf-8") as fh:
            for row in csv.reader(fh):
                if not row:
                    continue
                if total == 0 and rejected == 0 and row[0] == "radio":
                    continue  # header row
                try:
                    mcc, _ = parse_row(row)
                except ValueError:
                    rejected += 1
                    continue
                f = handles.get(mcc)
                if f is None:
                    f = handles[mcc] = open(
                        os.path.join(tmp, "%d.csv" % mcc), "w",
                        newline="", encoding="utf-8")
                _, k = parse_row(row)
                # Zero-padded sort key so a plain string sort is the order.
                f.write("%06d %06d %010d %s\t%s\n" % (k[0], k[1], k[2], k[3], ",".join(row)))
                total += 1
        for f in handles.values():
            f.close()

        files = []
        for mcc in sorted(handles):
            with open(os.path.join(tmp, "%d.csv" % mcc), encoding="utf-8") as fh:
                rows = sorted(fh)
            rows = [r.split("\t", 1)[1] for r in rows]
            name = "%d.csv.gz" % mcc

            def body(gz, rows=rows):
                gz.write("".join(rows).encode("utf-8"))

            path = os.path.join(out_dir, name)
            _write_gz(path, body)
            with open(path, "rb") as fh:
                data = fh.read()
            files.append({"mcc": mcc, "file": name, "rows": len(rows),
                          "bytes": len(data),
                          "sha256": hashlib.sha256(data).hexdigest()})
            os.remove(os.path.join(tmp, "%d.csv" % mcc))
    finally:
        for f in handles.values():
            if not f.closed:
                f.close()
        shutil.rmtree(tmp, ignore_errors=True)

    generated = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {"generatedAt": generated, "source": SOURCE, "licence": LICENCE,
                "credit": CREDIT, "files": files}
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    return {"rows": total, "rejected": rejected, "files": len(files)}


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    stats = split(argv[1], argv[2])
    print("split: %(rows)d rows into %(files)d files, %(rejected)d rejected" % stats)
    if stats["rows"] == 0:
        print("split: no valid rows", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
