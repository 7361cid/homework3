#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler, HTTPStatus
from scoring import get_score, get_interests

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = HTTPStatus.OK
BAD_REQUEST = HTTPStatus.BAD_REQUEST
FORBIDDEN = HTTPStatus.FORBIDDEN
NOT_FOUND = HTTPStatus.NOT_FOUND
INVALID_REQUEST = HTTPStatus.UNPROCESSABLE_ENTITY
INTERNAL_ERROR = HTTPStatus.INTERNAL_SERVER_ERROR
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


class ValidationError(Exception):
    pass


class Field:
    def __init__(self, required, nullable=False):
        self.required = required
        self.nullable = nullable
        self.value = None
        self.field_name = None

    def validate(self, value):
        if value is None and self.nullable:
            return True
        if value is None and not self.nullable:
            raise ValidationError(f"error: None in not nullable field")
        if value is not None:
            return False

    def __set_name__(self, owner, name):
        self.field_name = name

    def __set__(self, instance, value):
        self.validate(value)

    def __get__(self, instance, owner):
        return self.value


class CharField(Field):
    def validate(self, value):
        if super().validate(value):
            return
        if not isinstance(value, str):
            raise ValidationError(f"error: {self.field_name} must be string")

    def __add__(self, other):
        if isinstance(other, str):
            self.value = self.value + other
        elif isinstance(other, CharField):
            self.value = self.value + other.value


class ArgumentsField(Field):
    def validate(self, value):
        if super().validate(value):
            return
        if isinstance(value, dict):
            try:
                json.dumps(value)
            except json.JSONDecodeError:
                raise ValidationError("error: arguments JSONDecodeError")
        else:
            raise ValidationError(f"error: arguments bad type {type(value)}")


class EmailField(Field):
    def validate(self, value):
        if super().validate(value):
            return
        if isinstance(value, str):
            if '@' not in value:
                raise ValidationError("error: email without @")


class PhoneField(Field):
    def validate(self, value):
        if super().validate(value):
            return
        if isinstance(value, str):
            if len(value) != 11:
                raise ValidationError("error: phone length not equal 11")
            elif value[0] != "7":
                raise ValidationError("error: phone must start with 7")
            elif not value.isdigit():
                raise ValidationError("error: phone must be number or string of numbers")
        elif isinstance(value, int):
            if str(value)[0] != "7":
                raise ValidationError("error: phone must start with 7")
            elif len(str(value)) != 11:
                raise ValidationError("error: phone length not equal 11")
        else:
            raise ValidationError("error: phone bad data type")


class DateField(Field):
    def validate(self, value):
        if super().validate(value):
            return
        try:
            datetime.datetime.strptime(value, '%d.%m.%Y')
        except ValueError:
            raise ValidationError("error: date not in format dd.mm.yyyy")


class BirthDayField(DateField):
    def validate(self, value):
        try:
            super().validate(value=value)
        except ValidationError:
            raise ValidationError("error: birthday not in format dd.mm.yyyy")
        if value is None and self.nullable:
            return
        now_date = datetime.datetime.today().date()
        date_value = datetime.datetime.strptime(value, '%d.%m.%Y')
        date_value = datetime.datetime.date(date_value)
        if now_date - date_value > datetime.timedelta(days=70 * 365):
            raise ValidationError("error:  bad birthday You're over 70")


class GenderField(Field):
    def validate(self, value):
        if super().validate(value):
            return
        if value not in [0, 1, 2]:
            raise ValidationError("error: gender must be 0 or 1 or 2")


class ClientIDsField(Field):
    def validate(self, value):
        if super().validate(value):
            return
        if type(value) is list:
            if len(value) == 0:
                raise ValidationError("error: client_ids is empty list")
            for num in value:
                if type(num) is not int:
                    raise ValidationError("error: not number in client_ids")
            return value
        else:
            raise ValidationError("error: client_ids not list")


class Meta(type):
    def __new__(cls, name, bases, dct, validators_type):
        new_class = super().__new__(cls, name, bases, dct)
        if validators_type == 1:
            new_class.client_ids_validator = ClientIDsField(required=True)
            new_class.date_validator = DateField(required=False, nullable=True)
        if validators_type == 2:
            new_class.last_name_validator = CharField(required=False, nullable=True)
            new_class.first_name_validator = CharField(required=False, nullable=True)
            new_class.phone_validator = PhoneField(required=False, nullable=True)
            new_class.birthday_validator = BirthDayField(required=False, nullable=True)
            new_class.email_validator = EmailField(required=False, nullable=True)
            new_class.gender_validator = GenderField(required=False, nullable=True)
        if validators_type == 3:
            new_class.account_validator = CharField(required=False, nullable=True)
            new_class.login_validator = CharField(required=True, nullable=True)
            new_class.token_validator = CharField(required=True, nullable=True)
            new_class.arguments_validator = ArgumentsField(required=True, nullable=True)
            new_class.method_validator = CharField(required=True, nullable=False)
        return new_class


class ClientsInterestsRequest(metaclass=Meta, validators_type=1):
    def __init__(self, client_ids=None, date=None):
        self.client_ids = self.client_ids_validator = client_ids
        self.date = self.date_validator = date
        self.init_complete = True


class OnlineScoreRequest(metaclass=Meta, validators_type=2):
    def __init__(self, first_name=None, last_name=None, email=None, phone=None, birthday=None, gender=None):
        self.first_name = self.first_name_validator = first_name
        self.last_name = self.last_name_validator = last_name
        self.email = self.email_validator = email
        self.phone = self.phone_validator = phone
        self.birthday = self.birthday_validator = birthday
        self.gender = self.gender_validator = gender

    def find_score(self):
        return get_score(store=None, phone=self.phone, email=self.email, birthday=self.birthday,
                         gender=self.gender, first_name=self.first_name, last_name=self.last_name)


class MethodRequest(metaclass=Meta, validators_type=3):
    def __init__(self, account, login, token, arguments, method):
        self.account = self.account_validator = account
        self.login = self.login_validator = login
        self.token = self.token_validator = token
        self.arguments = self.arguments_validator = arguments
        self.method = self.method_validator = method

    @staticmethod
    def validate(request_body):
        fields = ["account", "login", "token", "arguments", "method"]
        for field in fields:
            if field not in request_body:
                raise ValidationError(f"Не хватает поля {field}")

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
                score = get_score(store=store, phone=OnlineScoreRequest_obj.phone, email=OnlineScoreRequest_obj.email,
                                  birthday=OnlineScoreRequest_obj.birthday, gender=OnlineScoreRequest_obj.gender,
                                  first_name=OnlineScoreRequest_obj.first_name,
                                  last_name=OnlineScoreRequest_obj.last_name)
                return {"score": score}, OK
            elif MethodRequest_obj.method == "clients_interests":
                ctx["nclients"] = len(MethodRequest_obj.arguments["client_ids"])
                ClientsInterestsRequest_obj = ClientsInterestsRequest(**MethodRequest_obj.arguments)
                interests = {}
                for id in ClientsInterestsRequest_obj.client_ids:
                    interests[str(id)] = get_interests(store=None, cid=id)
                return {"interests": interests}, OK
            else:
                return ERRORS[NOT_FOUND], NOT_FOUND
        else:
            return ERRORS[FORBIDDEN], FORBIDDEN
    except (ValidationError, KeyError) as exc:
        return ERRORS[INVALID_REQUEST] + " " + str(exc), INVALID_REQUEST


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
