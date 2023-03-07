import unittest
import argparse

from src.bucketcloner import main


class TestCLI(unittest.TestCase):
    def test_invalid_CLI_parameter(self):
        with self.assertRaises((argparse.ArgumentError, SystemExit), msg="Too few command line arguments"):
            main([])

        with self.assertRaises((argparse.ArgumentError, SystemExit), msg="Unknown command"):
            main(["false command"])
