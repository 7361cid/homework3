import os
import sys

import unittest
import threading


from pathlib import Path

path = str(Path(os.path.abspath(__file__)).parent.parent.parent)
sys.path.insert(1, path)
import api

class TestSuite(unittest.TestCase):
    def setUp(self):
        pass
    def make_request_to_server(self):
        pass
