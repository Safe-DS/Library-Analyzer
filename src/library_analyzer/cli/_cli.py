import argparse
import logging

# noinspection PyUnresolvedReferences,PyProtectedMember
from argparse import _SubParsersAction
from pathlib import Path

from library_analyzer.cli._run_annotations import _run_annotations
from library_analyzer.cli._run_api import _run_api_command
from library_analyzer.cli._run_migrate import _run_migrate_command
from library_analyzer.cli._run_usages import _run_usages_command
from library_analyzer.processing.api.docstring_parsing import DocstringStyle

_API_COMMAND = "api"
_USAGES_COMMAND = "usages"
_ANNOTATIONS_COMMAND = "annotations"
_MIGRATE_COMMAND = "migrate"


def cli() -> None:
    args = _get_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    if args.command == _API_COMMAND:
        _run_api_command(args.package, args.src, args.out, args.docstyle)
    elif args.command == _USAGES_COMMAND:
        _run_usages_command(args.package, args.client, args.out, args.processes, args.batchsize)
    elif args.command == _ANNOTATIONS_COMMAND:
        _run_annotations(args.api, args.usages, args.out)
    elif args.command == _MIGRATE_COMMAND:
        _run_migrate_command(args.apiv1, args.annotations, args.apiv2, args.out)


def _get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Python code.")
    parser.add_argument("-v", "--verbose", help="show info messages", action="store_true")

    # Commands
    subparsers = parser.add_subparsers(dest="command")
    _add_api_subparser(subparsers)
    _add_usages_subparser(subparsers)
    _add_annotations_subparser(subparsers)
    _add_migrate_subparser(subparsers)

    return parser.parse_args()


def _add_api_subparser(subparsers: _SubParsersAction) -> None:
    api_parser = subparsers.add_parser(_API_COMMAND, help="List the API of a package.")
    api_parser.add_argument(
        "-p",
        "--package",
        help="The name of the package.",
        type=str,
        required=True,
    )
    api_parser.add_argument(
        "-s",
        "--src",
        help="Directory containing the Python code of the package. If this is omitted, we try to locate the package "
        "with the given name in the current Python interpreter.",
        type=Path,
        required=False,
        default=None,
    )
    api_parser.add_argument("-o", "--out", help="Output directory.", type=Path, required=True)
    api_parser.add_argument(
        "--docstyle",
        help="The docstring style.",
        type=DocstringStyle.from_string,
        choices=list(DocstringStyle),
        required=False,
        default=DocstringStyle.PLAINTEXT.name,
    )


def _add_usages_subparser(subparsers: _SubParsersAction) -> None:
    usages_parser = subparsers.add_parser(_USAGES_COMMAND, help="Find usages of API elements.")
    usages_parser.add_argument(
        "-p",
        "--package",
        help="The name of the package. It must be installed in the current interpreter.",
        type=str,
        required=True,
    )
    usages_parser.add_argument(
        "-c",
        "--client",
        help="Directory containing Python code that uses the package.",
        type=Path,
        required=True,
    )
    usages_parser.add_argument(
        "--processes",
        help="How many processes should be spawned during processing.",
        type=int,
        required=False,
        default=4,
    )
    usages_parser.add_argument(
        "--batchsize",
        help="How many files to process in one go. Higher values lead to higher memory usage but better performance.",
        type=int,
        required=False,
        default=100,
    )
    usages_parser.add_argument("-o", "--out", help="Output directory.", type=Path, required=True)


def _add_annotations_subparser(subparsers: _SubParsersAction) -> None:
    generate_parser = subparsers.add_parser(_ANNOTATIONS_COMMAND, help="Generate Annotations automatically.")
    generate_parser.add_argument(
        "-a",
        "--api",
        help="File created by the 'api' command.",
        type=Path,
        required=True,
    )
    generate_parser.add_argument(
        "-u",
        "--usages",
        help="File created by the 'usages' command that contains usage counts.",
        type=Path,
        required=True,
    )
    generate_parser.add_argument("-o", "--out", help="Output directory.", type=Path, required=True)


def _add_migrate_subparser(subparsers: _SubParsersAction) -> None:
    generate_parser = subparsers.add_parser(
        _MIGRATE_COMMAND,
        help="Migrate Annotations for the new version based on the previous version.",
    )
    generate_parser.add_argument(
        "-a1",
        "--apiv1",
        help="File created with the 'api' command from the previous version.",
        type=Path,
        required=True,
    )
    generate_parser.add_argument(
        "-a2",
        "--apiv2",
        help="File created by the 'api' command from the new version.",
        type=Path,
        required=True,
    )
    generate_parser.add_argument(
        "-a",
        "--annotations",
        help="File that includes all annotations of the previous version.",
        type=Path,
        required=True,
    )
    generate_parser.add_argument("-o", "--out", help="Output directory.", type=Path, required=True)
