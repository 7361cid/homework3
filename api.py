#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import datetime
import logging
import hashlib
import time
import uuid
import redis
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

from scoring import get_score, get_interests

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class ValidateError(Exception):
    pass


class Field:
    def __init__(self, required, nullable=False, field_name=""):
        self.required = required
        self.nullable = nullable
        self.value = None
        self.field_name = ""  # для логирования часто используемых типов полей, в этом случае для CharField

    def validate(self, value):
        return value

    def set_value(self, value):
        self.validate(value)
        self.value = value


class CharField(Field):
    def validate(self, value):
        if value is None and self.nullable:
            return True
        if isinstance(value, str):
            return True
        else:
            raise ValidateError(f"error: {self.field_name} must be string")

    def __add__(self, other):
        if isinstance(other, str):
            self.value = self.value + other
        elif isinstance(other, CharField):
            self.value = self.value + other.value


class ArgumentsField(Field):
    def validate(self, value):
        if self.value is None and self.nullable:
            return True
        if type(value) == dict:
            try:
                json.dumps(value)
                return True
            except json.JSONDecodeError:
                raise ValidateError("error: arguments JSONDecodeError")
        else:
            raise ValidateError(f"error: arguments bad type {type(value)}")


class EmailField(Field):
    def validate(self, value):
        if value is None and self.nullable:
            return True
        if isinstance(value, str):
            if '@' in value:
                return True
            else:
                raise ValidateError("error: email without @")
        else:
            raise ValidateError(f"error: email bad type {type(value)}")


class PhoneField(Field):
    def validate(self, value):
        if value is None and self.nullable:
            return True
        if isinstance(value, str):
            if len(value) != 11:
                raise ValidateError("error: phone length not equal 11")
            elif value[0] != "7":
                raise ValidateError("error: phone must start with 7")
            elif not value.isdigit():
                raise ValidateError("error: phone must be number or string of numbers")
            else:
                return True
        elif isinstance(value, int):
            if str(value)[0] != "7":
                raise ValidateError("error: phone must start with 7")
            elif len(str(value)) != 11:
                raise ValidateError("error: phone length not equal 11")
            else:
                return True
        else:
            raise ValidateError("error: phone bad data type")



class DateField(Field):
    def validate(self, value):
        if value is None and self.nullable:
            return True
        try:
            datetime.datetime.strptime(value, '%d.%m.%Y')
            return True
        except ValueError:
            raise ValidateError("error: date not in format dd.mm.yyyy")


class BirthDayField(DateField):
    def validate(self, value):
        try:
            super().validate(value=value)
        except ValidateError:
            raise ValidateError("error: birthday not in format dd.mm.yyyy")
        if value is None and self.nullable:
            return True
        now_date = datetime.datetime.today().__format__('%d.%m.%Y')
        now_date = datetime.datetime.strptime(now_date, '%d.%m.%Y')
        date_value = datetime.datetime.strptime(value, '%d.%m.%Y')
        if now_date - date_value > datetime.timedelta(days=70 * 365):
            raise ValidateError("error:  bad birthday You're over 70")


class GenderField(Field):
    def validate(self, value):
        if value is None and self.nullable:
            return True
        if value in [0, 1, 2]:
            return True
        else:
            raise ValidateError("error: gender must be 0 or 1 or 2")


class ClientIDsField(Field):
    def validate(self, value):
        if value is None:
            if self.nullable:
                return True
            else:
                raise ValidateError("error: client_ids is empty")
        if type(value) is list:
            if len(value) == 0:
                raise ValidateError("error: client_ids is empty list")
            for num in value:
                if type(num) is not int:
                    raise ValidateError("error: not number in client_ids")
            return True
        else:
            raise ValidateError("error: client_ids not list")


class ClientsInterestsRequest:
    init_complete = False
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def __init__(self, client_ids=None, date=None):
        self.client_ids.set_value(client_ids)
        self.date.set_value(date)
        self.init_complete = True

    def __getattribute__(self, item):
        item_list = ["client_ids", "date"]
        if item in item_list and self.init_complete:
            return object.__getattribute__(self, item).value
        return object.__getattribute__(self, item)

    def find_interests(self, store):
        intersts = {}
        for id in self.client_ids:
            intersts[str(id)] = get_interests(store=store, cid=id)
        return intersts


class OnlineScoreRequest:
    init_complete = False
    first_name = CharField(required=False, nullable=True, field_name="first_name")
    last_name = CharField(required=False, nullable=True, field_name="last_name")
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, first_name=None, last_name=None, email=None, phone=None, birthday=None, gender=None):
        self.first_name.set_value(first_name)
        self.last_name.set_value(last_name)
        self.email.set_value(email)
        self.phone.set_value(phone)
        self.birthday.set_value(birthday)
        self.gender.set_value(gender)
        self.init_complete = True

    def __getattribute__(self, item):
        item_list = ["first_name", "last_name", "email", "phone", "birthday", "gender"]
        if item in item_list and self.init_complete:
            return object.__getattribute__(self, item).value
        return object.__getattribute__(self, item)

    def find_score(self, store):
        return get_score(store=store, phone=self.phone, email=self.email, birthday=self.birthday,
                         gender=self.gender, first_name=self.first_name, last_name=self.last_name)


class MethodRequest:
    init_complete = False
    account = CharField(required=False, nullable=True, field_name="account")
    login = CharField(required=True, nullable=True, field_name="login")
    token = CharField(required=True, nullable=True, field_name="token")
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False, field_name="method")

    def __init__(self, account, login, token, arguments, method):
        self.account.set_value(account)
        self.login.set_value(login)
        self.token.set_value(token)
        self.arguments.set_value(arguments)
        self.method.set_value(method)
        self.init_complete = True

    def __getattribute__(self, item):
        item_list = ["account", "login", "token", "arguments", "method"]
        if item in item_list and self.init_complete:
            return object.__getattribute__(self, item).value
        return object.__getattribute__(self, item)

    @staticmethod
    def validate(request_body):
        fields = ["account", "login", "token", "arguments", "method"]
        for field in fields:
            if field not in request_body:
                raise ValidateError(f"Не хватает поля {field}")

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode('utf-8')).hexdigest()
    else:
        digest = hashlib.sha512((request.account + request.login + SALT).encode('utf-8')).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    try:
        request_body = request['body']
        MethodRequest.validate(request_body)
        MethodRequest_obj = MethodRequest(account=request_body['account'], login=request_body['login'],
                                          token=request_body['token'], arguments=request_body['arguments'],
                                          method=request_body['method'])
        ctx["has"] = sorted(MethodRequest_obj.arguments.keys())
        if check_auth(MethodRequest_obj):
            if MethodRequest_obj.method == "online_score":
                if MethodRequest_obj.is_admin:
                    return {"score": 42}, OK
                OnlineScoreRequest_obj = OnlineScoreRequest(**MethodRequest_obj.arguments)
                score = OnlineScoreRequest_obj.find_score(store)
                return {"score": score}, OK
            elif MethodRequest_obj.method == "clients_interests":
                ctx["nclients"] = len(MethodRequest_obj.arguments["client_ids"])
                ClientsInterestsRequest_obj = ClientsInterestsRequest(**MethodRequest_obj.arguments)
                interests = ClientsInterestsRequest_obj.find_interests(store)
                return {"interests": interests}, OK
            else:
                return ERRORS[NOT_FOUND], NOT_FOUND
        else:
            return ERRORS[FORBIDDEN], FORBIDDEN
    except (ValidateError, KeyError) as exc:
        return ERRORS[INVALID_REQUEST] + " " + str(exc), INVALID_REQUEST


class RetrieException(Exception):
    pass


class Store:
    """
    Use Redis-x64-3.0.504
    """
    def __init__(self, retries=3, timeout=5):
        self.redis = redis.StrictRedis(host='localhost', port=6379, db=0)
        self.retries = retries
        self.timeout = timeout

    def set(self, key, value):
        return self.redis.set(key, value)

    def get(self, key):
        retries = self.retries
        while retries:
            try:
                return self.redis.get(key)
            except redis.exceptions.ConnectionError:
                time.sleep(self.timeout)
                retries -= 1
        raise RetrieException

    def cache_get(self, key):
        """
        Отрабатывает в любом случае
        """
        try:
            self.get(key)
        except Exception:
            return 0

    def cache_set(self, key, value, time):
        self.set(key, value)


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = Store()

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if type(response) == bytes:  # Иначе ошибка json.dumps
            response = response.decode(encoding="utf-8")
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode(encoding="utf-8"))  # Иначе ошибка отправки через сокет
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
