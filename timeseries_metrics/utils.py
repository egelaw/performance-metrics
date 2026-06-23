from __future__ import annotations

from pathlib import Path
import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, r2_score
import difflib
from typing import Sequence
import re
try:
    from properscoring import crps_ensemble
except Exception:  # pragma: no cover - optional
    crps_ensemble = None


METRIC_INFO = [
    {"metric": "r2", "label": "R2", "ideal": 1.0, "direction": "higher"},
    {"metric": "nse", "label": "NSE", "ideal": 1.0, "direction": "higher"},
    {"metric": "log_nse", "label": "log-NSE", "ideal": 1.0, "direction": "higher"},
    {"metric": "mnse", "label": "mNSE", "ideal": 1.0, "direction": "higher"},
    {"metric": "rmse", "label": "RMSE", "ideal": 0.0, "direction": "lower"},
    {"metric": "nrmse_pct", "label": "NRMSE %", "ideal": 0.0, "direction": "lower"},
    {"metric": "mae", "label": "MAE", "ideal": 0.0, "direction": "lower"},
    {"metric": "medae", "label": "MedAE", "ideal": 0.0, "direction": "lower"},
    {"metric": "bias", "label": "Bias", "ideal": 0.0, "direction": "closer to 0"},
    {"metric": "pbias_%", "label": "PBIAS %", "ideal": 0.0, "direction": "closer to 0"},
    {"metric": "mape_%", "label": "MAPE %", "ideal": 0.0, "direction": "lower"},
    {"metric": "smape_%", "label": "sMAPE %", "ideal": 0.0, "direction": "lower"},
    {"metric": "mre_%", "label": "MRE %", "ideal": 0.0, "direction": "closer to 0"},
    {"metric": "pearson_r", "label": "Pearson r", "ideal": 1.0, "direction": "higher"},
    {"metric": "spearman_rho", "label": "Spearman rho", "ideal": 1.0, "direction": "higher"},
    {"metric": "kge", "label": "KGE", "ideal": 1.0, "direction": "higher"},
    {"metric": "rsr", "label": "RSR", "ideal": 0.0, "direction": "lower"},
    {"metric": "mase", "label": "MASE", "ideal": 0.0, "direction": "lower"},
    {"metric": "peak_err", "label": "Peak Err", "ideal": 0.0, "direction": "closer to 0"},
    {"metric": "peak_timing_err_days", "label": "Peak Timing Days", "ideal": 0.0, "direction": "closer to 0"},
]

LOG_NSE_NOTE = "Note: log-NSE is only defined when observed and modeled values are positive; otherwise it is shown as nan."
DEFAULT_DATE_COL = "   Date / Time"


def load_data(
    path: Path,
    *,
    observed_column: str | None = None,
    observed_pattern: str | None = None,
    date_col: str = DEFAULT_DATE_COL,
) -> tuple[pd.DataFrame, str, list[str]]:
    if not Path(path).exists():
        raise ValueError(f"Input path not found: {path}")
    if Path(path).is_dir():
        raise ValueError(f"Expected a file path but received a directory: {path}")

    try:
        df = pd.read_csv(path, sep="\t", engine="python", skiprows=[1], dtype=str)
    except Exception as exc:  # pragma: no cover - defensive
        logging.exception("Failed to read input file %s", path)
        raise ValueError(f"Could not read input file {path}: {exc}") from exc

    # Resolve observed column by explicit name, substring pattern, or auto-detect.
    if observed_column:
        if observed_column not in df.columns:
            raise ValueError(f"Observed column {observed_column!r} was not found in {path}.")
        observed_col = observed_column
    elif observed_pattern:
        matches = [c for c in df.columns if observed_pattern.lower() in c.lower()]
        if not matches:
            raise ValueError(f"No column matching {observed_pattern!r} was found in {path}.")
        observed_col = matches[0]
    else:
        # Auto-detect numeric candidate columns and prefer likely observed names
        cand_scores: dict[str, int] = {}
        numeric_counts: dict[str, int] = {}
        for c in df.columns:
            coerced = pd.to_numeric(df[c].replace({"": np.nan, " ": np.nan, "\t": np.nan}), errors="coerce")
            nonnull = int(coerced.notna().sum())
            numeric_counts[c] = nonnull
            if nonnull > 0:
                cand_scores[c] = nonnull

        # heuristics for observed column names
        preferred_keywords = ["elev", "stage", "wse", "water", "flow", "discharge", "obs", "meas", "usgs"]
        preferred = [c for c in cand_scores if any(kw in c.lower() for kw in preferred_keywords)]
        if preferred:
            # pick preferred with most non-nulls
            observed_col = max(preferred, key=lambda c: cand_scores.get(c, 0))
        elif cand_scores:
            # fall back to column with most numeric entries
            observed_col = max(cand_scores, key=lambda c: cand_scores[c])
        else:
            raise ValueError("Could not auto-detect observed column; provide --observed-column or --observed-pattern.")

    model_cols = [
        c
        for c in df.columns
        if c.strip() not in {"Ordinate", date_col.strip()}
        and c != observed_col
        and "Units" not in c
        and "Type" not in c
    ]

    for column in [observed_col] + model_cols:
        df[column] = pd.to_numeric(df[column].replace({"": np.nan, " ": np.nan, "\t": np.nan}), errors="coerce")

    return df, observed_col, model_cols


def write_metrics_csv(metrics: pd.DataFrame, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(out_path, index=False)
    return out_path


def _prepare_observed_frame(df: pd.DataFrame, observed_col: str, date_col: str) -> pd.DataFrame:
    observed = df[df[observed_col].notna()].copy()
    raw = observed[date_col].astype(str)

    # Try the common pattern first (split on comma, e.g. '01 Jan 2020, 00:00')
    parsed = pd.to_datetime(raw.str.split(",").str[0], format="%d %b %Y", errors="coerce")

    # Fallback to pandas flexible parser for other formats
    if parsed.isna().all():
        parsed = pd.to_datetime(raw, infer_datetime_format=True, errors="coerce")

    observed["date"] = parsed
    out = observed.dropna(subset=["date"]).sort_values("date")
    if out.empty:  # pragma: no cover - defensive
        logging.warning("No valid date rows found after parsing; check date column format")
    return out


def compute_metrics(
    df: pd.DataFrame,
    observed_col: str,
    model_cols: list[str],
    *,
    date_col: str = DEFAULT_DATE_COL,
) -> pd.DataFrame:
    observed = _prepare_observed_frame(df, observed_col, date_col)

    rows = []
    for column in model_cols:
        sub = observed[[observed_col, column, "date"]].dropna()
        y_true = sub[observed_col].to_numpy(dtype=float)
        y_pred = sub[column].to_numpy(dtype=float)
        sample_n = len(y_true)
        if sample_n == 0:
            continue

        residual = y_pred - y_true
        ss_res = float(np.sum((y_true - y_pred) ** 2))
        ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
        obs_mean = float(np.mean(y_true))
        obs_std = float(np.std(y_true, ddof=1)) if sample_n > 1 else float("nan")
        pred_mean = float(np.mean(y_pred))
        pred_std = float(np.std(y_pred, ddof=1)) if sample_n > 1 else float("nan")
        denom_range = float(np.max(y_true) - np.min(y_true))
        denom_mase = float(np.mean(np.abs(np.diff(y_true)))) if sample_n > 1 else float("nan")
        abs_obs = np.abs(y_true)
        abs_pred = np.abs(y_pred)
        zero_mask = abs_obs != 0

        log_nse = float("nan")
        if np.all(y_true > 0) and np.all(y_pred > 0):
            log_y_true = np.log(y_true)
            log_y_pred = np.log(y_pred)
            log_ss_res = float(np.sum((log_y_true - log_y_pred) ** 2))
            log_ss_tot = float(np.sum((log_y_true - np.mean(log_y_true)) ** 2))
            log_nse = float(1.0 - log_ss_res / log_ss_tot) if log_ss_tot != 0 else float("nan")

        pearson_r = float(np.corrcoef(y_true, y_pred)[0, 1]) if sample_n > 1 else float("nan")
        spearman_rho = float(spearmanr(y_true, y_pred).correlation) if sample_n > 1 else float("nan")
        if sample_n > 1 and np.isfinite(pearson_r) and np.isfinite(obs_std) and np.isfinite(pred_std) and obs_std != 0.0 and obs_mean != 0.0:
            alpha = pred_std / obs_std
            beta = pred_mean / obs_mean
            kge = float(1.0 - np.sqrt((pearson_r - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2))
        else:
            kge = float("nan")

        # KGE components exposed for diagnostics
        kge_rho = pearson_r
        kge_alpha = alpha if 'alpha' in locals() else float("nan")
        kge_beta = beta if 'beta' in locals() else float("nan")

        rsr = float(np.sqrt(np.mean((y_true - y_pred) ** 2)) / obs_std) if sample_n > 1 and np.isfinite(obs_std) and obs_std != 0.0 else float("nan")
        mase = float(np.mean(np.abs(residual)) / denom_mase) if sample_n > 1 and np.isfinite(denom_mase) and denom_mase != 0.0 else float("nan")

        peak_obs_idx = int(np.argmax(y_true))
        peak_pred_idx = int(np.argmax(y_pred))
        peak_err = float(y_pred[peak_pred_idx] - y_true[peak_obs_idx])
        peak_timing_err_days = float((sub.iloc[peak_pred_idx]["date"] - sub.iloc[peak_obs_idx]["date"]).days)

        with np.errstate(divide="ignore", invalid="ignore"):
            mape_values = np.where(zero_mask, np.abs((y_true - y_pred) / y_true) * 100.0, np.nan)
            mre_values = np.where(zero_mask, ((y_pred - y_true) / y_true) * 100.0, np.nan)
            smape_values = np.where(
                (abs_obs + abs_pred) != 0,
                (2.0 * np.abs(y_pred - y_true) / (abs_obs + abs_pred)) * 100.0,
                np.nan,
            )

        mnse_denom = float(np.sum(np.abs(y_true - np.mean(y_true))))
        mnse = float(1.0 - np.sum(np.abs(y_pred - y_true)) / mnse_denom) if mnse_denom != 0 else float("nan")
        rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

        # Willmott's index of agreement (d)
        denom_w = np.sum((np.abs(y_pred - np.mean(y_true)) + np.abs(y_true - np.mean(y_true))) ** 2)
        willmott_d = float(1.0 - np.sum((y_pred - y_true) ** 2) / denom_w) if denom_w != 0 else float("nan")

        # Volume / total relative error (%)
        total_obs = float(np.sum(y_true))
        total_pred = float(np.sum(y_pred))
        volume_err_pct = float(100.0 * (total_pred - total_obs) / total_obs) if total_obs != 0 else float("nan")

        # RMSE decomposition: systematic vs unsystematic
        mse = float(np.mean((y_true - y_pred) ** 2))
        mse_syst = float((np.mean(y_pred) - np.mean(y_true)) ** 2)
        mse_unsyst = float(mse - mse_syst) if mse - mse_syst > 0 else 0.0
        rmse_syst = float(np.sqrt(mse_syst))
        rmse_unsyst = float(np.sqrt(mse_unsyst))

        # Flow Duration Curve / quantile errors (percent error at select quantiles)
        quantiles = [0.01, 0.05, 0.1, 0.5, 0.9, 0.95, 0.99]
        q_obs = np.quantile(y_true, quantiles)
        q_pred = np.quantile(y_pred, quantiles)
        # percent error per quantile (pred-obs)/obs*100, guarded
        with np.errstate(divide='ignore', invalid='ignore'):
            q_err_pct = 100.0 * (q_pred - q_obs) / q_obs

        rows.append(
            {
                "model": column,
                "sample_n": sample_n,
                "r2": float(r2_score(y_true, y_pred)) if sample_n > 1 and ss_tot != 0 else float("nan"),
                "nse": float(1.0 - ss_res / ss_tot) if ss_tot != 0 else float("nan"),
                "log_nse": log_nse,
                "mnse": mnse,
                "rmse": rmse,
                "nrmse_pct": float(100.0 * rmse / denom_range) if denom_range != 0 else float("nan"),
                "mae": float(mean_absolute_error(y_true, y_pred)),
                "medae": float(np.median(np.abs(residual))),
                "bias": float(np.mean(residual)),
                "pbias_%": float(100.0 * np.sum(residual) / np.sum(y_true)) if np.sum(y_true) != 0 else float("nan"),
                "mape_%": float(np.nanmean(mape_values)),
                "smape_%": float(np.nanmean(smape_values)),
                "mre_%": float(np.nanmean(mre_values)),
                "pearson_r": pearson_r,
                "spearman_rho": spearman_rho,
                "kge": kge,
                "kge_rho": kge_rho,
                "kge_alpha": kge_alpha,
                "kge_beta": kge_beta,
                "willmott_d": willmott_d,
                "volume_err_%": volume_err_pct,
                "rmse_syst": rmse_syst,
                "rmse_unsyst": rmse_unsyst,
                "obs_std": obs_std,
                "pred_std": pred_std,
                "rsr": rsr,
                "mase": mase,
                "peak_err": peak_err,
                "peak_timing_err_days": peak_timing_err_days,
            }
        )

        # Attach quantile errors (per-model) as separate named fields
        for q, err in zip(quantiles, q_err_pct):
            qname = f"q{int(q*100)}_err_pct"
            rows[-1][qname] = float(err) if not np.isnan(err) else float("nan")

    # Detect ensemble groups by column naming convention: base_ens_001, base_ens_002, ...
    ens_pattern = re.compile(r"(?P<base>.+)_ens_\d+$")
    groups: dict[str, list[str]] = {}
    for c in model_cols:
        m = ens_pattern.match(c)
        if m:
            base = m.group("base")
            groups.setdefault(base, []).append(c)

    # For each ensemble group, compute probabilistic scores
    for base, members in groups.items():
        members_sorted = sorted(members)
        ens_df = observed[members_sorted].dropna()
        if ens_df.empty:
            continue
        y_true_e = observed.loc[ens_df.index, observed_col].to_numpy(dtype=float)
        ens_arr = ens_df.to_numpy(dtype=float)  # shape (n_times, n_members)

        # CRPS (mean over time) if properscoring available
        if crps_ensemble is not None:
            try:
                crps_vals = crps_ensemble(y_true_e, ens_arr)
                mean_crps = float(np.mean(crps_vals))
            except Exception:
                mean_crps = float("nan")
        else:
            mean_crps = float("nan")

        # PICP for central 90% interval (5th-95th percentiles)
        lower = np.percentile(ens_arr, 5, axis=1)
        upper = np.percentile(ens_arr, 95, axis=1)
        inside = (y_true_e >= lower) & (y_true_e <= upper)
        picp_90 = float(100.0 * np.mean(inside))

        # Interval score for 90% interval
        alpha = 0.10
        width = upper - lower
        below = np.maximum(lower - y_true_e, 0.0)
        above = np.maximum(y_true_e - upper, 0.0)
        interval_score_90 = float(np.mean(width + (2.0 / alpha) * below + (2.0 / alpha) * above))

        # Brier score for exceedance of the observed 90th percentile (threshold)
        # Define threshold as the observed 90th percentile of y_true
        thresh = np.percentile(y_true_e, 90)
        obs_binary = (y_true_e > thresh).astype(float)
        # probability that ensemble members exceed threshold
        prob_exceed = np.mean(ens_arr > thresh, axis=1)
        brier_90 = float(np.mean((prob_exceed - obs_binary) ** 2))

        rows.append(
            {
                "model": f"{base}_ens",
                "sample_n": int(len(y_true_e)),
                "mean_crps": mean_crps,
                "picp_90_%": picp_90,
                "interval_score_90": interval_score_90,
                "brier_90": brier_90,
            }
        )

        # Attach quantile errors as separate named fields
        for q, err in zip(quantiles, q_err_pct):
            # field name like q10_err_pct for 10th percentile
            qname = f"q{int(q*100)}_err_pct"
            rows[-1][qname] = float(err) if not np.isnan(err) else float("nan")

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["roughness_n"] = out["model"].str.extract(r"\(n=([0-9.]+)\)").astype(float)
    return out.sort_values("roughness_n", na_position="last")


def format_metric_legend() -> pd.DataFrame:
    return pd.DataFrame(METRIC_INFO)[["metric", "label", "ideal", "direction"]]


def format_grouped_metrics(metrics: pd.DataFrame) -> str:
    if metrics.empty:
        return "No matched model rows were found."

    model_rows = list(metrics.sort_values("roughness_n").iterrows())
    headers = ["Metric", "Ideal"] + [f"n={row[1]['roughness_n']:.2f} Value" for row in model_rows]

    table_rows = []
    for info in METRIC_INFO:
        row_values = [info["label"], f"{info['ideal']:.4f}"]
        for model_row in model_rows:
            value = model_row[1][info["metric"]]
            row_values.append(f"{value:.4f}" if pd.notna(value) else "nan")
        table_rows.append(row_values)

    widths = []
    for col_idx, header in enumerate(headers):
        cell_width = max(len(header), *(len(str(row[col_idx])) for row in table_rows))
        widths.append(cell_width)

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [border]
    lines.append("| " + " | ".join(f"{headers[i]:<{widths[i]}}" for i in range(len(headers))) + " |")
    lines.append(border)
    for row in table_rows:
        lines.append(
            "| "
            + " | ".join(
                f"{row[i]:<{widths[i]}}" if i == 0 else f"{row[i]:>{widths[i]}}" for i in range(len(row))
            )
            + " |"
        )
    lines.append(border)
    lines.append("")
    lines.append("Model order: " + ", ".join(f"n={row[1]['roughness_n']:.2f}" for row in model_rows))
    return "\n".join(lines)


def make_daily_plot(
    df: pd.DataFrame,
    observed_col: str,
    model_cols: list[str],
    *,
    title: str,
    ylabel: str,
    observed_label: str,
    plot_name: str,
    date_col: str = DEFAULT_DATE_COL,
    output_dir: Path | None = None,
) -> Path:
    observed = _prepare_observed_frame(df, observed_col, date_col)

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(observed["date"], observed[observed_col], label=observed_label, color="black", linewidth=2.2)

    for column in model_cols:
        series = observed[["date", column]].dropna()
        if series.empty:
            continue
        roughness = column.split("(n=")[-1].rstrip(")") if "(n=" in column else column
        ax.plot(series["date"], series[column], label=f"n={roughness}", linewidth=1.5)

    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(title="Series", fontsize=9)
    fig.autofmt_xdate()

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_path = output_dir / plot_name
    else:
        plot_path = Path(__file__).with_name(plot_name)

    fig.tight_layout()
    try:
        fig.savefig(plot_path, dpi=200, bbox_inches="tight")
    finally:
        plt.close(fig)
    return plot_path

