"""Example: reservoir/time-series comparison helper (generic)."""
from pathlib import Path

from metrics.utils import load_data, compute_metrics, format_grouped_metrics, make_daily_plot


DATA_PATH = Path("/path/to/your/data/reservoir_file.txt")


def main():
    df, observed_col, model_cols = load_data(DATA_PATH, observed_pattern="ObservedColumnName")
    metrics = compute_metrics(df, observed_col, model_cols)
    print(format_grouped_metrics(metrics))
    make_daily_plot(
        df,
        observed_col,
        model_cols,
        title="Reservoir WSE",
        ylabel="units",
        observed_label="Observed",
        plot_name="reservoir_plot.png",
    )


if __name__ == "__main__":
    main()
