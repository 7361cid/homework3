#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import datetime
import logging
import hashlib
import uuid
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


class Field:
    def __init__(self, required, nullable=False):
        self.required = required
        self.nullable = nullable
        self.value = None

    def validate(self, value):
        return value

    def set_value(self, value):
        if self.validate(value):
            self.value = value
        else:
            raise ValueError


class CharField(Field):
    def validate(self, value):
        if value is None and self.nullable:
            return True
        if isinstance(value, str):
            return True
        else:
            return False

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
                return False


class EmailField(Field):
    def validate(self, value):
        if value is None and self.nullable:
            return True
        if isinstance(value, str) and '@' in value:
            return True
        else:
            return False


class PhoneField(Field):
    def validate(self, value):
        if value is None and self.nullable:
            return True
        if isinstance(value, str) and len(value) == 11 and value[0] == "7" and value.isdigit():
            return True
        elif isinstance(value, int) and len(str(value)) == 11 and str(value)[0] == "7":
            return True
        else:
            return False


class DateField(Field):
    def validate(self, value):
        if value is None and self.nullable:
            return True
        try:
            datetime.datetime.strftime(value, '%d.%m.%Y')
            return True
        except ValueError:
            return False


class BirthDayField(DateField):
    def validate(self, value):
        if super().validate(value=value):
            print("STEP2")
            now_date = datetime.datetime.today().__format__('%d.%m.%Y')
            now_date = datetime.datetime.strptime(now_date, '%d.%m.%Y')
            if now_date - value > datetime.timedelta(days=70*365):
                return False
            else:
                return True
        else:
            return False


class GenderField(Field):
    def validate(self, value):
        if self.value is None and self.nullable:
            return True
        if value in [0, 1, 2]:
            return True
        else:
            return False


class ClientIDsField(Field):
    pass


class ClientsInterestsRequest:
    init_complete = False
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def __init__(self, client_ids, date):
        self.client_ids.set_value(client_ids)
        self.date.set_value(date)
        self.init_complete = True

    def __getattribute__(self, item):
        item_list = ["client_ids", "date"]
        if item in item_list and self.init_complete:
            return object.__getattribute__(self, item).value
        return object.__getattribute__(self, item)

    def find_interests(self):
        return get_interests(store=None, cid=self.client_ids)


class OnlineScoreRequest:
    init_complete = False
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, first_name, last_name, email, phone, birthday, gender):
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

    def find_score(self):
        return get_score(store=None, phone=self.phone, email=self.email, birthday=self.birthday,
                         gender=self.gender, first_name=self.first_name, last_name=self.last_name)


class MethodRequest:
    init_complete = False
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

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

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512((request.account + request.login + SALT).encode('utf-8')).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    request_body = request['body']
    MethodRequest_obj = MethodRequest(account=request_body['account'], login=request_body['login'],
                                      token=request_body['token'], arguments=request_body['arguments'],
                                      method=request_body['method'])
    if check_auth(MethodRequest_obj):
        if MethodRequest_obj.method == "online_score":
            OnlineScoreRequest_obj = OnlineScoreRequest(first_name=MethodRequest_obj.arguments["first_name"],
                                                        last_name=MethodRequest_obj.arguments["last_name"],
                                                        email=MethodRequest_obj.arguments["email"],
                                                        phone=MethodRequest_obj.arguments["phone"],
                                                        birthday=datetime.datetime.strptime(MethodRequest_obj.arguments["birthday"], '%d.%m.%Y'),
                                                        gender=MethodRequest_obj.arguments["gender"],
                                                        )
            score = OnlineScoreRequest_obj.find_score()
            print(f"score {score}")
            return f"{score}".encode('utf-8'), OK
        elif MethodRequest_obj.method == "clients_interests":
            ClientsInterestsRequest_obj = ClientsInterestsRequest(client_ids=MethodRequest_obj.arguments["client_ids"],
                                                                  date=MethodRequest_obj.arguments["date"])
            interests = ClientsInterestsRequest_obj.find_interests()
            print(f"interests {interests}")
        else:
            return ERRORS[NOT_FOUND], NOT_FOUND
    else:
        return ERRORS[FORBIDDEN], FORBIDDEN

    response, code = 1, 1
    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

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
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r))
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
