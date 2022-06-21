import os
import sys
import hashlib
import datetime
import functools
import unittest
import logging
from optparse import OptionParser
from mock import Mock
from pathlib import Path

path = str(Path(os.path.abspath(__file__)).parent.parent.parent)
sys.path.insert(1, path)
import api
import store


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                logging.info(f"Start test {f.__name__} case {c}")
                new_args = args + (c if isinstance(c, tuple) else (c,))
                try:
                    f(*new_args)
                except Exception as e:
                    logging.exception(f"Fail test {f.__name__} case {c} with {e}")
                    raise Exception

        return wrapper

    return decorator


class TestSuite(unittest.TestCase):
    def setUp(self):
        self.context = {}
        self.headers = {}
        self.store = api.Store()
        # заполнение данными для теста метода get_interests
        self.store.set(key="i:0", value="writing")
        self.store.set(key="i:1", value="reading")
        self.store.set(key="i:2", value="codding")
        self.store.set(key="i:3", value="running")

    def get_response(self, request):
        print(f"LOG request {request} \n\n  LOG headers  {self.headers} \n\n")
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    def set_valid_auth(self, request):
        if request.get("login") == api.ADMIN_LOGIN:
            request["token"] = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H")
                                               + api.ADMIN_SALT).encode('utf-8')).hexdigest()
        else:
            msg = request.get("account", "") + request.get("login", "") + api.SALT
            request["token"] = hashlib.sha512(msg.encode('utf-8')).hexdigest()

    def test_empty_request(self):
        _, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments": {}},
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "sdd", "arguments": {}},
        {"account": "horns&hoofs", "login": "admin", "method": "online_score", "token": "", "arguments": {}},
    ])
    def test_bad_auth(self, request):
        _, code = self.get_response(request)
        self.assertEqual(api.FORBIDDEN, code)

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score"},
        {"account": "horns&hoofs", "login": "h&f", "arguments": {}},
        {"account": "horns&hoofs", "method": "online_score", "arguments": {}},
    ])
    def test_invalid_method_request(self, request):
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertTrue(len(response))

    @cases([
        # {}  Может же быть пустым по заданию(все аргументы метода необязательны), мб его не сюда?
        # {"phone": "79175002040"},   Валидное значение в тесте не валидных?
        {"phone": "89175002040", "email": "stupnikov@otus.ru"},
        {"phone": "79175002040", "email": "stupnikovotus.ru"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": -1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": "1"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.1890"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "XXX"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000", "first_name": 1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "s", "last_name": 2},
        #   {"phone": "79175002040", "birthday": "01.01.2000", "first_name": "s"}, Валидное значение в тесте не валидных?
        {"email": "stupnikov@otus.ru", "gender": 1, "last_name": 2},
    ])
    def test_invalid_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases([
        {},
        {"phone": "79175002040", "email": "stupnikov@otus.ru"},
        {"phone": 79175002040, "email": "stupnikov@otus.ru"},
        {"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"},
        {"gender": 0, "birthday": "01.01.2000"},
        {"gender": 2, "birthday": "01.01.2000"},
        {"first_name": "a", "last_name": "b"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "a", "last_name": "b"},
    ])
    def test_ok_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        score = response.get("score")
        self.assertTrue(isinstance(score, (int, float)) and score >= 0, arguments)
        self.assertEqual(sorted(self.context["has"]), sorted(arguments.keys()))

    def test_ok_score_admin_request(self):
        arguments = {"phone": "79175002040", "email": "stupnikov@otus.ru"}
        request = {"account": "horns&hoofs", "login": "admin", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        score = response.get("score")
        self.assertEqual(score, 42)

    @cases([
        {},
        {"date": "20.07.2017"},
        {"client_ids": [], "date": "20.07.2017"},
        {"client_ids": {1: 2}, "date": "20.07.2017"},
        {"client_ids": ["1", "2"], "date": "20.07.2017"},
        {"client_ids": [1, 2], "date": "XXX"},
    ])
    def test_invalid_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases([
        {"client_ids": [1, 2, 3], "date": datetime.datetime.today().strftime("%d.%m.%Y")},
        {"client_ids": [1, 2], "date": "19.07.2017"},
        {"client_ids": [0]},
    ])
    def test_ok_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        self.assertEqual(len(arguments["client_ids"]), len(response.get("interests")))
        self.assertTrue(all(v and isinstance(v, list) and all(isinstance(i, str) for i in v)
                            for v in response.get('interests').values()))
        self.assertEqual(self.context.get("nclients"), len(arguments["client_ids"]))

    @cases([
        [{"phone": "89175002040"}, "Invalid Request error: phone must start with 7"],
        [{"phone": 89175002040}, "Invalid Request error: phone must start with 7"],
        [{"email": "stupnikovotus.ru"}, "Invalid Request error: email without @"],
        [{"email": 0}, "Invalid Request error: email bad type <class 'int'>"],
        [{"gender": -1}, "Invalid Request error: gender must be 0 or 1 or 2"],
        [{"first_name": 1}, "Invalid Request error: first_name must be string"],
        [{"last_name": 1}, "Invalid Request error: last_name must be string"],
        [{"birthday": "XXX"}, "Invalid Request error: birthday not in format dd.mm.yyyy"],
        [{"birthday": "01.10.1888"}, "Invalid Request error:  bad birthday You're over 70"],
    ])
    def test_errors_msg_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments[0]}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertEqual(response, arguments[1])

    @cases([
        [{"client_ids": [0], "date": "1907.2017"}, "Invalid Request error: date not in format dd.mm.yyyy"],
        [{"client_ids": []}, "Invalid Request error: client_ids is empty list"],
        [{"client_ids": "not list"}, "Invalid Request error: client_ids not list"],
    ])
    def test_errors_msg_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments[0]}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertEqual(response, arguments[1])

    @staticmethod
    def mock_method():
        raise store.RetrieException

    @cases([{}])
    def test_no_store_score_request(self, arguments):
        self.store.get = Mock(side_effect=store.RetrieException)
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score",
                       "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)

    @cases([{"client_ids": [0]}])
    def test_no_store_clients_interests(self, arguments):
        self.store.get = Mock(side_effect=store.RetrieException)
        with self.assertRaises(store.RetrieException):
            request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests",
                       "arguments": arguments}
            self.set_valid_auth(request)
            response, code = self.get_response(request)


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    unittest.main()
