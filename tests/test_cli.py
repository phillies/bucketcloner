import argparse

import pytest

from bucketcloner.main import main


def test_invalid_cli_parameter_too_few() -> None:
    with pytest.raises((argparse.ArgumentError, SystemExit)):
        main([])


def test_invalid_cli_parameter_unknown_command() -> None:
    with pytest.raises((argparse.ArgumentError, SystemExit)):
        main(["false command"])
