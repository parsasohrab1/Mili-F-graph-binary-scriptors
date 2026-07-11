"""Error analysis dashboard for VIO benchmarks."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from mili_vio.benchmark.metrics import BenchmarkComparison


def generate_dashboard(
    comparison: BenchmarkComparison,
    output_path: Path,
) -> Path:
    """Generate scenario-based error analysis dashboard."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle(
        f"VIO Benchmark — {comparison.dataset_name} ({comparison.scenario})",
        fontsize=14,
        fontweight="bold",
    )

    methods = ["Factor Graph", "EKF"]
    pos_errors = [
        comparison.factor_graph.position_error_m,
        comparison.ekf.position_error_m,
    ]
    ate_rmse = [
        comparison.factor_graph.ate_rmse_m,
        comparison.ekf.ate_rmse_m,
    ]
    opt_times = [
        comparison.factor_graph.optimization_time_ms,
        comparison.ekf.optimization_time_ms,
    ]

    colors = ["#2ecc71", "#e74c3c"]

    ax = axes[0, 0]
    bars = ax.bar(methods, pos_errors, color=colors, edgecolor="black", linewidth=0.5)
    ax.axhline(y=1.0, color="gray", linestyle="--", label="Acceptance (1.0m)")
    ax.set_ylabel("Position Error (m)")
    ax.set_title("Mean Position Error")
    ax.legend()
    for bar, val in zip(bars, pos_errors):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, f"{val:.3f}m", ha="center", fontsize=9)

    ax = axes[0, 1]
    bars = ax.bar(methods, ate_rmse, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("ATE RMSE (m)")
    ax.set_title("Absolute Trajectory Error (RMSE)")
    for bar, val in zip(bars, ate_rmse):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, f"{val:.3f}m", ha="center", fontsize=9)

    ax = axes[1, 0]
    bars = ax.bar(methods, opt_times, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("Time (ms)")
    ax.set_title("Processing Time")
    for bar, val in zip(bars, opt_times):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{val:.1f}ms", ha="center", fontsize=9)

    ax = axes[1, 1]
    metrics_labels = ["Repeatability", "Loop Closures", "Improvement %"]
    metrics_values = [
        comparison.factor_graph.repeatability_mean * 100,
        comparison.factor_graph.loop_closures,
        comparison.improvement_pct,
    ]
    bars = ax.bar(metrics_labels, metrics_values, color=["#3498db", "#9b59b6", "#f39c12"], edgecolor="black", linewidth=0.5)
    ax.axhline(y=30, color="gray", linestyle="--", label="30% improvement target")
    ax.set_title("Factor Graph Metrics")
    ax.legend()
    for bar, val in zip(bars, metrics_values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5, f"{val:.1f}", ha="center", fontsize=9)

    status = []
    if comparison.meets_position_spec:
        status.append("Position: PASS")
    else:
        status.append("Position: FAIL")
    if comparison.meets_improvement_spec:
        status.append("EKF improvement: PASS")
    else:
        status.append("EKF improvement: FAIL")
    fig.text(0.5, 0.02, " | ".join(status) + f" | Backend: {comparison.backend}", ha="center", fontsize=10)

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
