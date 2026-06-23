from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Optional
import logging

from timeseries_metrics.utils import (
    LOG_NSE_NOTE,
    compute_metrics,
    format_grouped_metrics,
    format_metric_legend,
    load_data,
    make_daily_plot,
)


PRESETS = {}


def parse_args() -> object:
    p = ArgumentParser(description="Generic observed vs modeled time series comparator.")
    p.add_argument("--preset", choices=list(PRESETS.keys()), help="Use a preset for common files.")
    p.add_argument("data_path", nargs="?", type=Path, help="Path to input text file (overrides preset).")
    p.add_argument("--observed-column", type=str, default=None, help="Exact observed column name to use.")
    p.add_argument("--observed-pattern", type=str, default=None, help="Substring to locate observed column (overrides preset).")
    p.add_argument("--title", type=str, default=None, help="Plot title")
    p.add_argument("--ylabel", type=str, default=None, help="Y-axis label")
    p.add_argument("--observed-label", type=str, default=None, help="Legend label for observed series")
    p.add_argument("--plot-name", type=str, default=None, help="Output PNG file name")
    p.add_argument("--output-dir", type=Path, default=None, help="Directory to write the plot to")
    p.add_argument("--metrics-out", type=Path, default=None, help="Path to write metrics CSV")
    p.add_argument("--output-prefix", type=str, default=None, help="Prefix for output files (plot/metrics) in output-dir")
    p.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    preset = PRESETS.get(args.preset) if args.preset else {}

    data_path: Optional[Path] = args.data_path or preset.get("data_path")
    if data_path is None:
        raise SystemExit("Provide a data_path or --preset")

    observed_pattern = args.observed_pattern or preset.get("observed_pattern")
    title = args.title or preset.get("title", "Observed vs Modeled")
    ylabel = args.ylabel or preset.get("ylabel", "")
    observed_label = args.observed_label or preset.get("observed_label", "Observed")
    plot_name = args.plot_name or preset.get("plot_name", "comparison_plot.png")
    output_prefix = args.output_prefix

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    try:
        df, observed_col, model_cols = load_data(
            data_path, observed_column=args.observed_column, observed_pattern=observed_pattern
        )
        metrics = compute_metrics(df, observed_col, model_cols)

        print(format_metric_legend().to_string(index=False, float_format=lambda x: f"{x:0.4f}"))
        print()
        print(LOG_NSE_NOTE)
        print()
        print(format_grouped_metrics(metrics))

        if args.output_dir and output_prefix:
            plot_name = f"{output_prefix}_{plot_name}"
        plot_path = make_daily_plot(
            df,
            observed_col,
            model_cols,
            title=title,
            ylabel=ylabel,
            observed_label=observed_label,
            plot_name=plot_name,
            output_dir=args.output_dir,
        )
        print(f"\nSaved daily plot to: {plot_path}")

        if args.metrics_out:
            metrics_out = Path(args.metrics_out)
            if metrics_out.is_dir():
                metrics_fname = f"{output_prefix + '_metrics' if output_prefix else 'metrics'}.csv"
                metrics_out = metrics_out / metrics_fname
            from timeseries_metrics.utils import write_metrics_csv

            written = write_metrics_csv(metrics, metrics_out)
            print(f"Saved metrics CSV to: {written}")
    except Exception as exc:  # pragma: no cover - top-level user-visible error
        logging.exception("Comparison failed")
        raise SystemExit(f"Error: {exc}") from exc


if __name__ == "__main__":
    main()
