# Time Series Metrics Comparator

[![License](https://img.shields.io/github/license/egelaw/performance-metrics)](LICENSE)

Lightweight Python scripts for comparing observed and modeled time series, computing standard performance metrics, and generating daily plots.

Files
- `metrics/utils.py` — shared data loading, metric computations, and plotting helpers.
- `compare_timeseries.py` — main Python script for generic observed vs modeled comparisons.
- `tests/` — unit tests for metrics and plotting.
- `requirements.txt` — minimal dependency list for running the scripts.

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

3. Run using the shell wrapper (simplest):

```bash
chmod +x run.sh
./run.sh /path/to/file.txt --observed-pattern "ObservedColumnName"
```

4. Or run the Python script directly:

```bash
python compare_timeseries.py /path/to/file.txt --observed-pattern "ObservedColumnName" --output-dir tmp_plots --metrics-out tmp_plots
```

5. Run with custom options:

```bash
./run.sh /path/to/file.txt --observed-pattern "ObservedColumnName" --plot-name myplot.png
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

**Ensembles & Probabilistic Metrics**

This tool supports simple ensemble/probabilistic forecasts using a naming convention for ensemble member columns and computes several probabilistic diagnostics automatically.

- Naming convention: name ensemble member columns using the pattern `<base>_ens_###` where `###` is a numeric member identifier (zero-padded is fine). Example column names:

	```csv
	Date / Time	Observed	Flow_ens_001	Flow_ens_002	Flow_ens_003	Flow_ens_004
	01 Jan 2020, 00:00	10.0	9.8	10.2	9.5	10.5
	```

- The tool will detect groups of columns sharing the same `<base>` (here `Flow`) and compute ensemble diagnostics for each group. No extra flag is required — columns following the naming pattern are grouped automatically.

Computed probabilistic metrics (per ensemble group)

- `picp_90_%`: Prediction Interval Coverage Probability for the central 90% interval — percent of observed values inside the ensemble 5th–95th percentile interval (close to 90% is ideal for calibrated ensembles).
- `interval_score_90`: Interval score for the 90% central prediction interval (lower is better, balances interval width and missed coverage).
- `brier_90`: Brier score for exceedance of the observed 90th percentile (0–1, lower is better) computed from ensemble exceedance probabilities.

Per-model diagnostics

- `willmott_d`: Willmott index of agreement (bounded 0–1; 1 is perfect agreement).
- `kge_rho`, `kge_alpha`, `kge_beta`: KGE components (correlation, variability ratio, bias ratio) useful for diagnosing why KGE may be low.
- `volume_err_%`: Percent error in total/volume between predicted and observed (useful for water-balance focused applications).
- `q10_err_pct`, `q50_err_pct`, `q90_err_pct`, etc.: Percent errors at selected quantiles (Flow Duration Curve errors) to evaluate behavior across low/median/high regimes.

Example: running the script with ensemble columns

```bash
# example CSV has columns: Date / Time, Observed, Flow_ens_001, Flow_ens_002, ...
python compare_timeseries.py /path/to/file.txt --observed-pattern "Observed" --output-dir out --metrics-out out

# The CSV output (if --metrics-out provided) will contain ensemble summary rows named Flow_ens
# and per-model rows will include the additional quantile and diagnostic columns described above.
```

## Metric References

The implementation in `metrics/utils.py` is annotated with source comments at the point where each metric is computed. The table below expands those references so the formula provenance is visible in the documentation as well.

| Metric | Source used in code |
| --- | --- |
| `r2` | [scikit-learn `r2_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.r2_score.html) / coefficient of determination |
| `nse` | [Nash and Sutcliffe (1970)](https://doi.org/10.1016/0022-1694(70)90255-6), *Journal of Hydrology* |
| `mnse` | Direct modified-NSE form used in hydrologic model evaluation; see the implementation comments in [metrics/utils.py](metrics/utils.py) |
| `rmse` | Standard RMSE definition; matches [HydroEval](https://thibhlln.github.io/hydroeval/) |
| `nrmse_pct` | RMSE normalized by the observed range, computed directly in this repo |
| `mae` | [scikit-learn mean absolute error](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html) |
| `medae` | [scikit-learn median absolute error](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.median_absolute_error.html) |
| `bias` | Mean signed error; direct formula |
| `pbias_%` | Percent bias as in [HydroEval](https://thibhlln.github.io/hydroeval/) |
| `mape_%` | [Hyndman and Koehler (2006)](https://doi.org/10.1016/j.ijforecast.2006.03.001), forecast accuracy measures |
| `smape_%` | [Hyndman and Koehler (2006)](https://doi.org/10.1016/j.ijforecast.2006.03.001), symmetric MAPE family |
| `mre_%` | Mean relative error, computed directly from the signed residuals |
| `pearson_r` | [Pearson correlation coefficient](https://docs.scipy.org/doc/numpy/reference/generated/numpy.corrcoef.html), standard definition |
| `spearman_rho` | [Spearman rank correlation coefficient](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html), standard definition |
| `kge` | [Gupta et al. (2009)](https://doi.org/10.1016/j.jhydrol.2009.08.003), original Kling-Gupta Efficiency |
| `kge_rho`, `kge_alpha`, `kge_beta` | [Gupta et al. (2009)](https://doi.org/10.1016/j.jhydrol.2009.08.003), KGE components |
| `rsr` | [Moriasi et al. (2007)](https://doi.org/10.13031/2013.23153), SWAT evaluation guidelines |
| `mase` | [Hyndman and Koehler (2006)](https://doi.org/10.1016/j.ijforecast.2006.03.001), Mean Absolute Scaled Error |
| `peak_err` | Direct peak-value diagnostic computed from the matched time stamps |
| `peak_timing_err_days` | Direct peak-timing diagnostic computed from the matched time stamps |
| `willmott_d` | [Willmott (1981)](https://doi.org/10.1175/1520-0450(1981)020%3C1201%3AIOAOTM%3E2.0.CO;2), index of agreement |
| `volume_err_%` | Direct percent volume bias from total observed vs modeled volume |
| `rmse_syst`, `rmse_unsyst` | Direct algebraic decomposition of MSE |
| `q10_err_pct`, `q50_err_pct`, `q90_err_pct`, etc. | Direct flow-duration-curve style quantile diagnostics |
| `picp_90_%` | Prediction interval coverage computed directly from the ensemble 5th-95th percentile band |
| `interval_score_90` | [Gneiting and Raftery (2007)](https://doi.org/10.1198/016214506000001437), interval score |
| `brier_90` | [Brier (1950)](https://journals.ametsoc.org/view/journals/mwre/78/1/1520-0493_1950_078_0001_voboaf_2_0_co_2.xml); threshold-exceedance form follows the proper-scoring-rule literature |

For the hydrologic metrics above, the code currently follows the same formulas used by the open-source HydroEval package where applicable. Metrics marked as "computed directly" are derived in this repository from standard definitions rather than copied from a third-party implementation.

License
- MIT-style: use as you like.
