import os
from pathlib import Path

import pandas as pd

from metrics.utils import (
    DEFAULT_DATE_COL,
    compute_metrics,
    make_daily_plot,
)


def make_sample_df(tmp_path: Path) -> pd.DataFrame:
    dates = ["01 Jan 2020, 00:00", "02 Jan 2020, 00:00", "03 Jan 2020, 00:00", "04 Jan 2020, 00:00"]
    obs = [10.0, 12.0, 11.0, 13.0]
    model_a = [9.5, 12.5, 10.0, 14.0]
    model_b = [0.0, 0.0, 0.0, 0.0]

    df = pd.DataFrame({
        "Ordinate": ["1"] * 4,
        DEFAULT_DATE_COL: dates,
        "Observed": obs,
        "Model_A (n=4)": model_a,
        "Model_B (n=4)": model_b,
    })
    return df


def test_compute_metrics_basic(tmp_path: Path):
    df = make_sample_df(tmp_path)
    metrics = compute_metrics(df, "Observed", ["Model_A (n=4)", "Model_B (n=4)"], date_col=DEFAULT_DATE_COL)
    assert not metrics.empty
    # expect core deterministic metrics
    assert "r2" in metrics.columns
    assert "nse" in metrics.columns
    # new metrics
    assert "willmott_d" in metrics.columns
    assert "kge_rho" in metrics.columns
    assert "volume_err_%" in metrics.columns
    assert "q10_err_pct" in metrics.columns


def test_make_daily_plot_writes_file(tmp_path: Path):
    df = make_sample_df(tmp_path)
    out_dir = tmp_path / "plots"
    out = make_daily_plot(
        df,
        "Observed",
        ["Model_A (n=4)", "Model_B (n=4)"],
        title="Test",
        ylabel="Units",
        observed_label="Obs",
        plot_name="test_plot.png",
        date_col=DEFAULT_DATE_COL,
        output_dir=out_dir,
    )
    assert out.exists()
    assert out.suffix == ".png"


def test_probabilistic_metrics(tmp_path: Path):
    # Create observed and ensemble members
    dates = ["01 Jan 2020, 00:00", "02 Jan 2020, 00:00", "03 Jan 2020, 00:00", "04 Jan 2020, 00:00"]
    obs = [10.0, 12.0, 11.0, 13.0]
    # create 5 ensemble members with small perturbations
    ens = [[9.0, 10.5, 11.2, 12.8], [10.2, 12.1, 10.9, 13.3], [10.0, 11.9, 11.0, 12.7], [9.8, 12.2, 11.1, 13.0], [10.5, 12.0, 11.3, 12.9]]
    df = pd.DataFrame({
        "Ordinate": ["1"] * 4,
        DEFAULT_DATE_COL: dates,
        "Observed": obs,
    })
    # add ensemble member columns
    for i, member in enumerate(ens, start=1):
        df[f"Flow_ens_{i:03d}"] = member

    df = df
    metrics = compute_metrics(df, "Observed", [c for c in df.columns if "Flow_ens_" in c], date_col=DEFAULT_DATE_COL)
    # ensemble summary row should exist
    assert any(metrics["model"].astype(str).str.contains("Flow_ens"))
