# Time Series Metrics Comparator

[![License](https://img.shields.io/github/license/egelaw/performance-metrics)](LICENSE) [![CI](https://github.com/egelaw/performance-metrics/actions/workflows/ci.yml/badge.svg)](https://github.com/egelaw/performance-metrics/actions)

Small utilities to compare an observed time series against modeled/estimated time series and produce performance metrics and a daily plot.

Files
- `timeseries_metrics/utils.py` — shared data loading, metric computations, and plotting helpers.
- `compare_timeseries.py` — single CLI entrypoint for generic observed vs modeled comparisons.
- `tests/` — unit tests for metrics and plotting.

Quick start

1. Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the generic comparator:

```bash
python compare_timeseries.py /path/to/file.txt --observed-pattern "ObservedColumnName" --output-dir tmp_plots --metrics-out tmp_plots
```

4. Or run with a custom file and options:

```bash
python compare_timeseries.py /path/to/file.txt --observed-pattern "ObservedColumnName" --plot-name myplot.png
```

Additional options

- `--output-dir DIR` — write the PNG into `DIR` (created if necessary).
- `--verbose` — enable debug logging for troubleshooting.
- `--metrics-out PATH` — write computed metrics to CSV (file or directory).
- `--output-prefix PREFIX` — prefix for generated plot and metrics files when using `--output-dir`.

Running tests

```bash
pip install -r requirements.txt
pip install pytest
pytest -q
```

Notes
- The scripts only compare model values at timestamps where an observed daily value exists (no temporal aggregation).
- `log-NSE` requires strictly positive values; when undefined it will be shown as `nan`.

License
- MIT-style: use as you like.
