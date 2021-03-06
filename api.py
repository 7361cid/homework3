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
    def __init__(self, required, nullable=False, field_name=None):
        self.required = required
        self.nullable = nullable
        self.value = None
        self.field_name = field_name

    def validate(self, value):
        if value is None and self.nullable:
            return True
        if value is None and not self.nullable:
            raise ValidationError(f"error: None in not nullable field")
        if value is not None:
            return False


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
        else:
            raise ValidationError(f"error: email bad type {type(value)}")


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
        if isinstance(value, list):
            if len(value) == 0:
                raise ValidationError("error: client_ids is empty list")
            for num in value:
                if not isinstance(num, int):
                    raise ValidationError("error: not number in client_ids")
            return value
        else:
            raise ValidationError("error: client_ids not list")


class RequestMeta(type):
    def __new__(mcs, name, bases, attrs):
        field_list = []
        for k, v in attrs.items():
            if isinstance(v, Field):
                v.field_name = k
                field_list.append(v)
        cls = super(RequestMeta, mcs).__new__(mcs, name, bases, attrs)
        cls.fields = field_list
        return cls


class BaseRequest:
    def __init__(self, **kwargs):
        for field in self.fields:
            if field.field_name in kwargs:
                setattr(self, field.field_name, kwargs[field.field_name])
            else:
                setattr(self, field.field_name, None)

    def validate_data(self):
        for field in self.fields:
            field.validate(getattr(self, field.field_name, None))


class ClientsInterestsRequest(BaseRequest, metaclass=RequestMeta):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(BaseRequest, metaclass=RequestMeta):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


class MethodRequest(BaseRequest, metaclass=RequestMeta):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def make_request(ctx, store, MethodRequest_obj):
    if MethodRequest_obj.method == "online_score":
        if MethodRequest_obj.is_admin:
            return {"score": 42}, OK
        OnlineScoreRequest_obj = OnlineScoreRequest(**MethodRequest_obj.arguments)
        OnlineScoreRequest_obj.validate_data()
        score = get_score(store=store, phone=OnlineScoreRequest_obj.phone, email=OnlineScoreRequest_obj.email,
                          birthday=OnlineScoreRequest_obj.birthday, gender=OnlineScoreRequest_obj.gender,
                          first_name=OnlineScoreRequest_obj.first_name,
                          last_name=OnlineScoreRequest_obj.last_name)
        return {"score": score}, OK
    elif MethodRequest_obj.method == "clients_interests":
        ctx["has"] = sorted(MethodRequest_obj.arguments.keys())
        ctx["nclients"] = len(MethodRequest_obj.arguments["client_ids"])
        ClientsInterestsRequest_obj = ClientsInterestsRequest(**MethodRequest_obj.arguments)
        ClientsInterestsRequest_obj.validate_data()
        interests = {}
        for id in ClientsInterestsRequest_obj.client_ids:
            interests[str(id)] = get_interests(store=None, cid=id)
        return {"interests": interests}, OK
    else:
        return ERRORS[NOT_FOUND], NOT_FOUND


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
        MethodRequest_obj = MethodRequest(account=request_body['account'], login=request_body['login'],
                                          token=request_body['token'], arguments=request_body['arguments'],
                                          method=request_body['method'])
        ctx["has"] = sorted(MethodRequest_obj.arguments.keys())
        if check_auth(MethodRequest_obj):
            return make_request(ctx, store, MethodRequest_obj)
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
        if isinstance(response, bytes):  # ?????????? ???????????? json.dumps
            response = response.decode(encoding="utf-8")
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode(encoding="utf-8"))  # ?????????? ???????????? ???????????????? ?????????? ??????????
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
