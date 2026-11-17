import argparse
import sys
from pathlib import Path

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze Enron email metadata without processing message content."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to the read-only email corpus directory.",
    )
    parser.add_argument(
        "--key-file",
        type=Path,
        required=True,
        help="Path to the HMAC key file; pass a mounted file, not the key itself.",
    )
    parser.add_argument(
        "--alias-map",
        type=Path,
        help="Optional external JSON map of exact email aliases to canonical addresses.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for pseudonymized analytical outputs.",
    )
    parser.add_argument(
        "--min-edge-count",
        type=int,
        default=5,
        help="Privacy-assessment edge suppression threshold (default: 5).",
    )
    parser.add_argument(
        "--export-edges",
        action="store_true",
        help=(
            "Write sensitive pseudonymized node-level edge CSVs. The privacy "
            "report's mailbox-corpus test does not evaluate the customer "
            "public-information threat model."
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.min_edge_count < 1:
        parser.error("--min-edge-count must be at least 1")
    if args.export_edges:
        print(
            "WARNING: node-level edge exports are sensitive. The mailbox-corpus "
            "test in privacy_assessment.json does not evaluate the customer "
            "public-information threat model.",
            file=sys.stderr,
        )
    try:
        run_pipeline(
            data_dir=args.data_dir,
            key_file=args.key_file,
            output_dir=args.output_dir,
            min_edge_count=args.min_edge_count,
            alias_map_file=args.alias_map,
            export_edges=args.export_edges,
        )
    except ValueError as error:
        parser.error(str(error))
    except OSError:
        parser.error("pipeline could not read input or write outputs")
    return 0
