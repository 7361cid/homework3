import os
import sys
import unittest
import requests
import redis
from threading import Thread
from unittest import mock
from pathlib import Path

path = str(Path(os.path.abspath(__file__)).parent.parent.parent)
sys.path.insert(1, path)
import api
import store


class TestStore(unittest.TestCase):
    def setUp(self):
        self.store = store.Store()

    def test_set_get_value(self):
        self.store.set(key="key", value=1)
        self.assertEqual(int(self.store.get(key="key").decode("utf-8")), 1)

    @staticmethod
    def error(key):
        raise redis.exceptions.ConnectionError()

    @mock.patch('store.Store._get')
    def test_retries(self, mock_obj):
        self.assertEqual(self.store.retries, 3)
        mock_obj.side_effect = self.error
        self.store.set(key="key", value=1)
        with self.assertRaises(store.RetrieException):
            self.store.get(key="key")
        self.assertEqual(self.store.retries, 3)

    @mock.patch('store.Store._get')
    def test_cache_get(self, mock_obj):
        self.assertEqual(self.store.retries, 3)
        mock_obj.side_effect = self.error
        self.store.set(key="key", value=1)
        value = self.store.cache_get(key="key")
        self.assertEqual(value, 0)


class TestServer(unittest.TestCase):
    def setUp(self):
        thread1 = Thread(target=api.main)
        thread1.start()

    def test_request_to_server_200(self):
        data = {'account': 'horns&hoofs', 'login': 'h&f', 'method': 'online_score',
                'arguments': {'phone': '79175002040', 'email': 'stupnikov@otus.ru', 'gender': 1,
                              'birthday': '01.01.2000', 'first_name': 'a', 'last_name': 'b'},
                'token': '55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7'
                         'd89b6d718a9e35af34e14e1d5bcd5a08f21fc95'}
        headers = {"Content-Length": str(len(str(data)))}
        response = requests.post('http://localhost:8080/method', headers=headers, json=data)
        self.assertEqual(response.status_code, 200)

    def test_request_to_server_404(self):
        data = {'account': 'horns&hoofs', 'login': 'h&f', 'method': 'online_score',
                'arguments': {'phone': '79175002040', 'email': 'stupnikov@otus.ru', 'gender': 1,
                              'birthday': '01.01.2000', 'first_name': 'a', 'last_name': 'b'},
                'token': '55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7'
                         'd89b6d718a9e35af34e14e1d5bcd5a08f21fc95'}
        headers = {"Content-Length": str(len(str(data)))}
        response = requests.post('http://localhost:8080/bad_method', headers=headers, json=data)
        self.assertEqual(response.status_code, 404)

    def test_request_to_server_no_auth(self):
        data = {'account': 'horns&hoofs', 'login': 'h&f', 'method': 'online_score',
                'arguments': {'phone': '79175002040', 'email': 'stupnikov@otus.ru', 'gender': 1,
                              'birthday': '01.01.2000', 'first_name': 'a', 'last_name': 'b'},
                'token': ''}
        headers = {"Content-Length": str(len(str(data)))}
        response = requests.post('http://localhost:8080/method', headers=headers, json=data)
        self.assertEqual(response.status_code, 403)

    def test_request_to_server_bad_data(self):
        data = {'account': 'horns&hoofs', 'login': 'h&f', 'method': 'online_score',
                'arguments': {'phone': 'error', 'email': 'stupnikov@otus.ru', 'gender': 1,
                              'birthday': '01.01.2000', 'first_name': 'a', 'last_name': 'b'},
                'token': '55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7'
                         'd89b6d718a9e35af34e14e1d5bcd5a08f21fc95'}
        headers = {"Content-Length": str(len(str(data)))}
        response = requests.post('http://localhost:8080/method', headers=headers, json=data)
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
