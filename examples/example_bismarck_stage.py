"""Example: stage comparison helper (migrated from legacy script).

This is provided as an example for how to call the generic comparator utilities
against a tab-separated timeseries file. It is NOT required for the core library.
"""
from pathlib import Path

from timeseries_metrics.utils import load_data, compute_metrics, format_grouped_metrics, make_daily_plot


DATA_PATH = Path("/path/to/your/data/stage_file.txt")


def main():
    df, observed_col, model_cols = load_data(DATA_PATH, observed_pattern="Elevatoin_datum_adjusted")
    metrics = compute_metrics(df, observed_col, model_cols)
    print(format_grouped_metrics(metrics))
    make_daily_plot(df, observed_col, model_cols, title="Stage", ylabel="units", observed_label="Observed", plot_name="stage_plot.png")


if __name__ == "__main__":
    main()
