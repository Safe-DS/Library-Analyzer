import subprocess


def test_cli_api() -> None:
    subprocess.run(
        ["poetry", "run", "analyze-library", "api", "-p", "library_analyzer", "-s", "src", "-o", "out"],
        check=True
    )


def test_cli_usages() -> None:
    subprocess.run(
        ["poetry", "run", "analyze-library", "usages", "-p", "library_analyzer", "-c", "library_analyzer", "-o", "out"],
        check=True
    )


def test_cli_annotations() -> None:
    subprocess.run(
        ["poetry", "run", "analyze-library", "annotations", "-a", "tests/data/removeAnnotations/api_data.json", "-u",
         "tests/data/removeAnnotations/usage_data.json", "-o", "out/annotations.json"],
        check=True
    )


def test_cli_all() -> None:
    subprocess.run(
        ["poetry", "run", "analyze-library", "all", "-p", "library_analyzer", "-s", "src", "-c",
         "library_analyzer", "-o", "out"],
        check=True
    )


def test_cli_migration() -> None:
    subprocess.run(
        ["poetry", "run", "analyze-library", "migrate", "-a1", "tests/data/migration/apiv1_data.json", "-a2",
         "tests/data/migration/apiv2_data.json", "-a", "tests/data/migration/annotationv1.json", "-o", "out"],
        check=True
    )
