import os
from pathlib import Path

import pandas as pd

from timeseries_metrics.utils import (
    DEFAULT_DATE_COL,
    compute_metrics,
    make_daily_plot,
)


def make_sample_df(tmp_path: Path) -> pd.DataFrame:
    dates = ["01 Jan 2020, 00:00", "02 Jan 2020, 00:00", "03 Jan 2020, 00:00", "04 Jan 2020, 00:00"]
    obs = [10.0, 12.0, 11.0, 13.0]
    model_a = [9.5, 12.5, 10.0, 14.0]
    model_b = [0.0, 0.0, 0.0, 0.0]  # edge-case zeros (log-NSE undefined)

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
    # expect columns for r2 and log_nse
    assert "r2" in metrics.columns
    assert "log_nse" in metrics.columns
    # Model_B has zeros; log_nse should be nan for that row
    mb = metrics[metrics["model"] == "Model_B (n=4)"]
    assert mb["log_nse"].isna().all()


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
