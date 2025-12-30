import argparse

import pytest

from bucketcloner.main import main


def test_invalid_CLI_parameter_too_few():
    with pytest.raises((argparse.ArgumentError, SystemExit)):
        main([])


def test_invalid_CLI_parameter_unknown_command():
    with pytest.raises((argparse.ArgumentError, SystemExit)):
        main(["false command"])
