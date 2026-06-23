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

**Ensembles & Probabilistic Metrics**

This tool supports simple ensemble/probabilistic forecasts using a naming convention for ensemble member columns and computes several probabilistic diagnostics automatically.

- Naming convention: name ensemble member columns using the pattern `<base>_ens_###` where `###` is a numeric member identifier (zero-padded is fine). Example column names:

	```csv
	Date / Time	Observed	Flow_ens_001	Flow_ens_002	Flow_ens_003	Flow_ens_004
	01 Jan 2020, 00:00	10.0	9.8	10.2	9.5	10.5
	```

- The tool will detect groups of columns sharing the same `<base>` (here `Flow`) and compute ensemble diagnostics for each group. No extra CLI flag is required — columns following the naming pattern are grouped automatically.

Computed probabilistic metrics (per ensemble group)

- `mean_crps`: Continuous Ranked Probability Score averaged over time (lower is better). Requires the `properscoring` package; if unavailable the value will be `nan`.
- `picp_90_%`: Prediction Interval Coverage Probability for the central 90% interval — percent of observed values inside the ensemble 5th–95th percentile interval (close to 90% is ideal for calibrated ensembles).
- `interval_score_90`: Interval score for the 90% central prediction interval (lower is better, balances interval width and missed coverage).
- `brier_90`: Brier score for exceedance of the observed 90th percentile (0–1, lower is better) computed from ensemble exceedance probabilities.

Per-model diagnostics

- `willmott_d`: Willmott index of agreement (bounded 0–1; 1 is perfect agreement).
- `kge_rho`, `kge_alpha`, `kge_beta`: KGE components (correlation, variability ratio, bias ratio) useful for diagnosing why KGE may be low.
- `volume_err_%`: Percent error in total/volume between predicted and observed (useful for water-balance focused applications).
- `q10_err_pct`, `q50_err_pct`, `q90_err_pct`, etc.: Percent errors at selected quantiles (Flow Duration Curve errors) to evaluate behavior across low/median/high regimes.

Example: running the CLI with ensemble columns

```bash
# example CSV has columns: Date / Time, Observed, Flow_ens_001, Flow_ens_002, ...
python compare_timeseries.py /path/to/file.txt --observed-pattern "Observed" --output-dir out --metrics-out out

# The CSV output (if --metrics-out provided) will contain ensemble summary rows named Flow_ens
# and per-model rows will include the additional quantile and diagnostic columns described above.
```
