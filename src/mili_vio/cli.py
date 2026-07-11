"""Command-line interface for Mili VIO."""

from __future__ import annotations

import argparse
from pathlib import Path

from mili_vio.config import load_config
from mili_vio.data import CooperativeVIODataGenerator, print_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cooperative VIO data generation and utilities",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to YAML config file (default: configs/default.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/cooperative_vio_data.csv"),
        help="Output CSV path",
    )
    parser.add_argument(
        "--groups",
        type=int,
        default=None,
        help="Override number of groups",
    )
    parser.add_argument(
        "--drones",
        type=int,
        default=None,
        help="Override drones per group",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Override time steps per drone",
    )

    args = parser.parse_args()
    config = load_config(args.config)

    if args.groups is not None:
        config.data_generation.num_groups = args.groups
    if args.drones is not None:
        config.data_generation.drones_per_group = args.drones
    if args.steps is not None:
        config.data_generation.time_steps = args.steps

    generator = CooperativeVIODataGenerator(config=config)
    df = generator.save(args.output)

    print_summary(df)
    print(f"\nFile saved: {args.output}")
    print("Product 2 data generation complete!")


if __name__ == "__main__":
    main()
