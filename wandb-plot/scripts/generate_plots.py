#!/usr/bin/env python3
"""Generate line plots from W&B run metrics using matplotlib.

This script generates publication-quality line plots from metric data,
with intelligent axis scaling and optional smoothing.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Iterable
from datetime import datetime

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd

from scripts.wandb_utils import (
    get_run,
    setup_logging,
    WandBAuthError,
    progress_wrap,
    resolve_output_dir,
    safe_filename,
    write_metadata_json,
)


def time_weighted_ema(
    x_values: Iterable[float],
    y_values: Iterable[float],
    weight: float,
    viewport_scale: float
) -> List[float]:
    """Compute debiased, time-weighted EMA matching W&B's TWEMA behavior."""
    x_list = list(x_values)
    y_list = list(y_values)
    if not y_list:
        return []

    x_min = min(x_list) if x_list else 0.0
    x_max = max(x_list) if x_list else 0.0
    range_of_x = float(x_max - x_min) if x_list else 0.0
    if range_of_x <= 0:
        range_of_x = 1.0

    last_y = 0.0
    debias_weight = 0.0
    smoothed = []

    for idx, y_point in enumerate(y_list):
        prev_idx = idx - 1 if idx > 0 else 0
        delta = x_list[idx] - x_list[prev_idx] if x_list else 1.0
        if hasattr(delta, "total_seconds"):
            delta = delta.total_seconds()
        change_in_x = (float(delta) / range_of_x) * viewport_scale
        smoothing_weight_adj = weight ** change_in_x

        last_y = last_y * smoothing_weight_adj + y_point
        debias_weight = debias_weight * smoothing_weight_adj + 1.0
        smoothed.append(last_y / debias_weight)

    return smoothed


def determine_x_axis(
    df: pd.DataFrame
) -> Tuple[pd.Series, str, Optional[str]]:
    """Determine x-axis data and label for a dataframe."""
    if '_step' in df.columns:
        return df['_step'], 'Step', '_step'
    if '_timestamp' in df.columns:
        return df['_timestamp'], 'Timestamp', '_timestamp'
    return pd.Series(df.index), 'Index', None


def plot_metric(
    run_data: List[Tuple[str, pd.DataFrame]],
    metric: str,
    output_path: str,
    smooth: Optional[int] = None,
    ema_weight: Optional[float] = 0.99,
    ema_enabled: bool = True,
    viewport_scale: float = 1000.0
):
    """
    Generate a single metric plot.

    Args:
        run_data: List of (label, DataFrame) pairs with metric data
        metric: Name of metric column to plot
        output_path: Path to save plot
        smooth: Optional rolling average window size
        ema_weight: EMA weight (0-1) when enabled
        ema_enabled: Whether to render EMA-smoothed line

    Raises:
        ValueError: If metric not in DataFrame
    """
    if not run_data:
        raise ValueError("No run data provided for plotting")

    plt.figure(figsize=(10, 6))

    x_label = None
    x_key = None
    for _, df in run_data:
        x_data, x_label, x_key = determine_x_axis(df)
        if x_key:
            break
    if x_label is None:
        x_label = 'Index'

    colors = plt.get_cmap('tab10')
    multiple_runs = len(run_data) > 1
    used_labels = set()

    lines_plotted = 0

    for idx, (label, df) in enumerate(run_data):
        if metric not in df.columns:
            continue

        if x_key and x_key in df.columns:
            x_data = df[x_key]
        else:
            x_data = pd.Series(df.index)
        y_data = df[metric]

        mask = ~y_data.isna()
        x_data = x_data[mask]
        y_data = y_data[mask]

        if len(y_data) == 0:
            continue

        color = colors(idx % colors.N)
        plot_label = label
        if plot_label in used_labels:
            plot_label = f"{label} ({idx + 1})"
        used_labels.add(plot_label)

        if smooth and smooth > 1:
            y_series = pd.Series(y_data.values)
            y_smoothed = y_series.rolling(window=smooth, min_periods=1).mean()
            y_data_smoothed = y_smoothed.values
            plt.plot(x_data, y_data, linewidth=1, alpha=0.25, color=color)
            plt.plot(x_data, y_data_smoothed, linewidth=2, alpha=0.9, color=color, label=plot_label)
            lines_plotted += 1
        elif ema_enabled and ema_weight is not None:
            y_smoothed = time_weighted_ema(x_data, y_data, ema_weight, viewport_scale)
            plt.plot(x_data, y_data, linewidth=1, alpha=0.25, color=color)
            plt.plot(x_data, y_smoothed, linewidth=2, alpha=0.9, color=color, label=plot_label)
            lines_plotted += 1
        else:
            plt.plot(x_data, y_data, linewidth=2, alpha=0.85, color=color, label=plot_label)
            lines_plotted += 1

    if lines_plotted == 0:
        raise ValueError(f"Metric '{metric}' has no valid data points")

    if multiple_runs:
        plt.legend()

    # Labels and title
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(metric, fontsize=12)
    plt.title(f'{metric}', fontsize=14, pad=20)

    # Grid
    plt.grid(True, alpha=0.3, linestyle='--')

    # Intelligent y-axis scaling
    metric_values = []
    for _, df in run_data:
        if metric in df.columns:
            metric_values.append(df[metric].dropna())
    if metric_values:
        all_values = pd.concat(metric_values)
        if 'loss' in metric.lower():
            positive = all_values[all_values > 0]
            if not positive.empty:
                y_min, y_max = positive.min(), positive.max()
                if y_min > 0 and (y_max / y_min) > 10:
                    plt.yscale('log')
                    plt.ylabel(f'{metric} (log scale)', fontsize=12)
        elif 'acc' in metric.lower() or 'accuracy' in metric.lower():
            if all_values.max() <= 1.0 and all_values.min() >= 0.0:
                plt.ylim(-0.05, 1.05)

    # Tight layout
    plt.tight_layout()

    # Save figure
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Generated: {output_path}")


def generate_plots(
    entity_project: str,
    run_id: str,
    metrics: List[str],
    full_resolution: bool = False,
    output_dir: Optional[str] = None,
    smooth: Optional[int] = None,
    ema_weight: Optional[float] = 0.99,
    ema_enabled: bool = True,
    viewport_scale: float = 1000.0,
    group_by_prefix: bool = False,
    all_metrics: bool = False,
    include_system: bool = False
) -> List[str]:
    """
    Generate plots from metric data.

    Args:
        entity_project: Project in format "entity/project" or "project"
        run_id: Run ID or name
        metrics: List of metric names to plot
        full_resolution: If True, use scan_history() for all data points
        output_dir: Optional custom output directory
        smooth: Optional rolling average window size
        ema_weight: EMA weight (0-1) when enabled
        ema_enabled: Whether to render EMA-smoothed line
        viewport_scale: Scale factor for time-weighted EMA normalization
        group_by_prefix: If True, group metrics by prefix folder (e.g., rewards/* -> rewards/)
        all_metrics: If True, plot all available metrics
        include_system: If True, include system metrics (prefixed with "_") when plotting all metrics

    Returns:
        List of generated file paths

    Raises:
        WandBAuthError: If not authenticated
        ValueError: If run or metrics not found

    Example:
        >>> plots = generate_plots(
        ...     "my-org/my-project",
        ...     "abc123",
        ...     ["loss", "accuracy"],
        ...     smooth=10
        ... )
        >>> print(f"Generated {len(plots)} plots")
    """
    logger = logging.getLogger(__name__)
    run_ids = [rid.strip() for rid in run_id.split(",") if rid.strip()]
    if not run_ids:
        raise ValueError("run_id cannot be empty")

    runs = []
    for rid in run_ids:
        runs.append(get_run(entity_project, rid))

    keys = None if all_metrics else list(dict.fromkeys(metrics + ["_step", "_timestamp"]))
    run_data = []
    for run in runs:
        try:
            if full_resolution:
                print("Fetching full resolution data (this may take a while)...")
                logger.info("Fetching full resolution data for run %s", run.id)
                history_data = []
                try:
                    iterator = run.scan_history(keys=keys)
                except TypeError:
                    iterator = run.scan_history()
                for row in progress_wrap(iterator, f"Fetching history {run.id}"):
                    history_data.append(row)
                df = pd.DataFrame(history_data)
            else:
                print("Fetching sampled data...")
                logger.info("Fetching sampled data for run %s", run.id)
                try:
                    df = run.history(keys=keys)
                except TypeError:
                    df = run.history()
        except Exception as e:
            raise ValueError(f"Error fetching run history: {str(e)}") from e

        if df.empty:
            raise ValueError(f"Run {run.id} has no history data")

        label = run.name or run.id
        run_data.append((label, df, run))

    # Verify metrics exist
    def is_system_metric(name: str) -> bool:
        return name.startswith("_") or name.startswith("system/")

    all_available = set()
    for _, df, _ in run_data:
        for col in df.columns:
            if include_system or not is_system_metric(col):
                all_available.add(col)

    if all_metrics:
        metrics = sorted(all_available)

    missing_metrics = [m for m in metrics if m not in all_available]

    if missing_metrics:
        available_metrics = sorted(all_available)
        error_msg = f"Metrics not found: {', '.join(missing_metrics)}\n"
        error_msg += f"Available metrics: {', '.join(available_metrics[:10])}"
        if len(available_metrics) > 10:
            error_msg += f" (+{len(available_metrics) - 10} more)"
        raise ValueError(error_msg)

    # Determine output directory (only after validation)
    if output_dir:
        output_path = Path(output_dir).expanduser()
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        output_path.mkdir(parents=True, exist_ok=True)
    elif len(runs) == 1:
        output_path = resolve_output_dir(entity_project, runs[0], output_dir=output_dir)
    else:
        base_dir = Path("wandb_plots")
        entity = getattr(runs[0], "entity", None) or "unknown-entity"
        project = getattr(runs[0], "project", None) or "unknown-project"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        compare_dir = f"compare_{timestamp}_{safe_filename('_'.join(run_ids))[:60]}"
        output_path = base_dir / f"{entity}_{project}" / compare_dir
        output_path.mkdir(parents=True, exist_ok=True)

    # Generate plots
    generated_paths = []

    for metric in progress_wrap(metrics, "Generating plots"):
        # Create safe filename
        safe_metric_name = safe_filename(metric)
        metric_output_path = output_path
        if group_by_prefix and "/" in metric:
            prefix = safe_filename(metric.split("/", 1)[0])
            metric_output_path = output_path / prefix
            metric_output_path.mkdir(parents=True, exist_ok=True)
        output_file = metric_output_path / f"{safe_metric_name}.png"

        try:
            plot_metric(
                [(label, df) for label, df, _ in run_data],
                metric,
                str(output_file),
                smooth=smooth,
                ema_weight=ema_weight,
                ema_enabled=ema_enabled,
                viewport_scale=viewport_scale
            )
            generated_paths.append(str(output_file))
        except Exception as e:
            logger.warning("Failed to generate plot for '%s': %s", metric, e)
            print(f"Warning: Failed to generate plot for '{metric}': {e}", file=sys.stderr)
            continue

    # Create metadata file
    if generated_paths:
        run_ids_out = [run.id for _, _, run in run_data]
        run_names_out = [run.name for _, _, run in run_data]
        metadata = {
            "run_id": run_ids_out[0] if len(run_ids_out) == 1 else None,
            "run_name": run_names_out[0] if len(run_names_out) == 1 else None,
            "run_ids": run_ids_out,
            "run_names": run_names_out,
            "entity": getattr(runs[0], "entity", None),
            "project": getattr(runs[0], "project", None),
            "generation_timestamp": datetime.now().isoformat(),
            "full_resolution": full_resolution,
            "smoothing_window": smooth,
            "ema_weight": ema_weight if ema_enabled else None,
            "ema_enabled": ema_enabled,
            "viewport_scale": viewport_scale if ema_enabled else None,
            "group_by_prefix": group_by_prefix,
            "metrics_plotted": metrics,
            "all_metrics": all_metrics,
            "include_system": include_system,
            "plots_generated": [str(Path(p).name) for p in generated_paths],
            "plot_count": len(generated_paths),
            "data_points": [len(df) for _, df, _ in run_data]
        }

        write_metadata_json(output_path, metadata, merge=True)

    return generated_paths


def main():
    """Main entry point for the script."""
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Generate line plots from W&B run metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate loss and accuracy plots
  %(prog)s my-org/my-project abc123 --metrics loss,accuracy

  # Full resolution with smoothing
  %(prog)s my-org/my-project abc123 --metrics loss --full-res --smooth 10

  # Multiple metrics
  %(prog)s my-org/my-project abc123 --metrics train/loss,val/loss,train/accuracy

  # Compare a metric across runs (comma-separated run ids)
  %(prog)s my-org/my-project run1,run2,run3 --metrics train/loss

  # Custom output directory
  %(prog)s my-org/my-project abc123 --metrics loss --output ./my_plots
        """
    )

    parser.add_argument(
        "entity_project",
        help="W&B project in format 'entity/project' or 'project'"
    )
    parser.add_argument(
        "run_id",
        help="Run ID or name (comma-separated for multiple runs)"
    )
    parser.add_argument(
        "--metrics",
        help="Comma-separated list of metrics to plot (e.g., 'loss,accuracy')"
    )
    parser.add_argument(
        "--all-metrics",
        action="store_true",
        help="Plot all available metrics"
    )
    parser.add_argument(
        "--full-res",
        action="store_true",
        help="Use full resolution data (slower, all data points)"
    )
    parser.add_argument(
        "--output",
        help="Custom output directory (default: wandb_plots/<entity>_<project>/<run>/)"
    )
    parser.add_argument(
        "--smooth",
        type=int,
        help="Apply rolling average smoothing with specified window size"
    )
    parser.add_argument(
        "--ema-weight",
        type=float,
        default=0.99,
        help="EMA smoothing weight (default: 0.99)"
    )
    parser.add_argument(
        "--viewport-scale",
        type=float,
        default=1000.0,
        help="Viewport scale for time-weighted EMA (default: 1000)"
    )
    parser.add_argument(
        "--group-by-prefix",
        action="store_true",
        help="Group metric outputs into subfolders by prefix (e.g., rewards/* -> rewards/)"
    )
    parser.add_argument(
        "--include-system",
        action="store_true",
        help="Include system metrics (prefixed with '_') when using --all-metrics"
    )
    parser.add_argument(
        "--no-ema",
        action="store_true",
        help="Disable EMA smoothing (shows only raw lines)"
    )

    args = parser.parse_args()

    # Parse metrics
    metrics_list = [m.strip() for m in args.metrics.split(',') if m.strip()] if args.metrics else []

    if args.all_metrics and metrics_list:
        print("Error: --metrics and --all-metrics cannot be used together", file=sys.stderr)
        return 1
    if not args.all_metrics and not metrics_list:
        print("Error: No metrics specified (use --metrics or --all-metrics)", file=sys.stderr)
        return 1

    try:
        # Generate plots
        if args.ema_weight <= 0 or args.ema_weight >= 1:
            raise ValueError("--ema-weight must be between 0 and 1 (exclusive)")

        if args.viewport_scale <= 0:
            raise ValueError("--viewport-scale must be positive")

        generated = generate_plots(
            args.entity_project,
            args.run_id,
            metrics_list,
            full_resolution=args.full_res,
            output_dir=args.output,
            smooth=args.smooth,
            ema_weight=args.ema_weight,
            ema_enabled=not args.no_ema,
            viewport_scale=args.viewport_scale,
            group_by_prefix=args.group_by_prefix,
            all_metrics=args.all_metrics,
            include_system=args.include_system
        )

        if generated:
            print(f"\nSuccessfully generated {len(generated)} plot(s):")
            for path in generated:
                print(f"  - {path}")
        else:
            print("\nNo plots were generated.")

        return 0

    except WandBAuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
