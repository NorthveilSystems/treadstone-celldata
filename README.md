# treadstone-celldata

A public mirror of the [OpenCelliD](https://opencellid.org) cell tower
database, split into one file per country (MCC) and published as GitHub
Releases. [Treadstone](https://github.com/NorthveilSystems) instances download
from here, so they need no OpenCelliD token and are not held to its limit of
two downloads per day.

This repository contains **only OpenCelliD data**. No Treadstone customer or
device data is ever stored here.

## Credit

> Cell tower data from [OpenCellID](https://opencellid.org), licensed under
> [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

## Licence

The data is © OpenCelliD contributors, licensed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). ShareAlike
applies: anything you derive from these files must carry the same licence and
the credit above. The scripts in this repository are released under the same
licence; see [LICENSE](LICENSE).

## Files

Each release (tagged `YYYY-MM`) holds:

- `<mcc>.csv.gz`: gzipped CSV without a header row, the 14 OpenCelliD columns in
  their original order (`radio,mcc,net,area,cell,unit,lon,lat,range,samples,changeable,created,updated,averageSignal`),
  rows sorted by `net, area, cell, radio`.
- `manifest.json`: `generatedAt`, `source`, `licence`, `credit` and, per file,
  `mcc`, `file`, `rows`, `bytes` and `sha256`. Check the hash before using a file.

The latest release is always at
`https://github.com/NorthveilSystems/treadstone-celldata/releases/latest/download/<file>`.

## Using it with Treadstone

Set, for the ingest service:

```
OPENCELLID_MIRROR_URL=https://github.com/NorthveilSystems/treadstone-celldata/releases/latest/download
```

Treadstone then fetches `manifest.json` and the `<mcc>.csv.gz` files it needs,
verifies their hashes, and shows the credit above in the Maps panel.

## Refresh schedule

A GitHub Actions workflow (`.github/workflows/mirror.yml`) runs on the 2nd of
every month at 04:00 UTC, and can be started by hand. It downloads the full
OpenCelliD export, runs `split.py`, and publishes a new release. The last three
releases are kept. The run fails, publishing nothing, if the download is under
50 MB or the row count falls by more than half against the previous release.

The workflow needs the repository secret `OPENCELLID_TOKEN` (an OpenCelliD API
token).

## Development

```
python3 -m unittest discover -s tests
python3 split.py cell_towers.csv.gz out
```

Python 3 standard library only.
