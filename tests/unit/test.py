import os
import unittest
import logging
import json
from optparse import OptionParser
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock as uMock

# Импорт без затрагивания sys.path
file = "api.py"
file2 = "store.py"
folder = str(Path(os.path.abspath(__file__)).parent.parent.parent)
store = SourceFileLoader(file2, folder + f"/{file2}").load_module()
api = SourceFileLoader(file, folder + f"/{file}").load_module()


class TestCharField(unittest.TestCase):
    def test_char_field_value(self):
        char_field_object = api.CharField(required=True, field_name="char_field_object")
        with self.assertRaises(api.ValidationError) as exc:
            char_field_object.validate(11)
        self.assertTrue('error: char_field_object must be string' in str(exc.exception))

    def test_char_field_nullable_false(self):
        char_field_object = api.CharField(required=True, nullable=False, field_name="char_field_object")
        with self.assertRaises(api.ValidationError):
            char_field_object.validate(None)

    def test_char_field_nullable_true(self):
        char_field_object = api.CharField(required=True, nullable=True, field_name="char_field_object")
        char_field_object.validate(None)


class TestEmailField(unittest.TestCase):
    def test_email_field_value(self):
        email_field_object = api.EmailField(required=True, field_name="email_field_object")
        with self.assertRaises(api.ValidationError) as exc:
            email_field_object.validate(11)
        self.assertTrue('error: email bad type' in str(exc.exception))

    def test_email_field_value2(self):
        email_field_object = api.EmailField(required=True, field_name="email_field_object")
        with self.assertRaises(api.ValidationError) as exc:
            email_field_object.validate('not_valid_string')
        self.assertTrue('error: email without @' in str(exc.exception))

    def test_email_field_nullable_false(self):
        email_field_object = api.EmailField(required=True, nullable=False, field_name="email_field_object")
        with self.assertRaises(api.ValidationError):
            email_field_object.validate(None)

    def test_email_field_nullable_true(self):
        char_field_object = api.EmailField(required=True, nullable=True, field_name="email_field_object")
        char_field_object.validate(None)


class TestPhoneField(unittest.TestCase):
    def test_phone_field_value(self):
        phone_field_object = api.PhoneField(required=True, field_name="phone_field_object")
        with self.assertRaises(api.ValidationError) as exc:
            phone_field_object.validate('not_valid_string')
        self.assertTrue('error: phone must be number or string of numbers' in str(exc.exception))

    def test_phone_field_value2(self):
        phone_field_object = api.PhoneField(required=True, field_name="phone_field_object")
        with self.assertRaises(api.ValidationError) as exc:
            phone_field_object.validate('89991233131')
        self.assertTrue('error: phone must start with 7' in str(exc.exception))

    def test_phone_field_value3(self):
        phone_field_object = api.PhoneField(required=True, field_name="phone_field_object")
        with self.assertRaises(api.ValidationError) as exc:
            phone_field_object.validate('89991233131111')
        self.assertTrue('error: phone length not equal 11' in str(exc.exception))

    def test_phone_field_nullable_false(self):
        phone_field_object = api.EmailField(required=True, nullable=False, field_name="phone_field_object")
        with self.assertRaises(api.ValidationError):
            phone_field_object.validate(None)

    def test_phone_field_nullable_true(self):
        phone_field_object = api.EmailField(required=True, nullable=True, field_name="phone_field_object")
        phone_field_object.validate(None)


class TestDateField(unittest.TestCase):
    def test_date_field_value(self):
        date_field_object = api.DateField(required=True, field_name="date_field_object")
        with self.assertRaises(api.ValidationError) as exc:
            date_field_object.validate('bad_date')
        self.assertTrue('error: date not in format dd.mm.yyyy' in str(exc.exception))

    def test_date_field_nullable_false(self):
        date_field_object = api.DateField(required=True, nullable=False, field_name="date_field_object")
        with self.assertRaises(api.ValidationError):
            date_field_object.validate(None)

    def test_date_field_nullable_true(self):
        date_field_object = api.DateField(required=True, nullable=True, field_name="date_field_object")
        date_field_object.validate(None)


class TestBirthDayField(unittest.TestCase):
    def test_birthday_field_value(self):
        birthday_field_object = api.BirthDayField(required=True, field_name="birthday_field_object")
        with self.assertRaises(api.ValidationError) as exc:
            birthday_field_object.validate('bad_date')
        self.assertTrue('birthday not in format dd.mm.yyyy' in str(exc.exception))

    def test_birthday_field_value2(self):
        birthday_field_object = api.BirthDayField(required=True, field_name="birthday_field_object")
        with self.assertRaises(api.ValidationError) as exc:
            birthday_field_object.validate('10.10.1900')
        self.assertTrue("bad birthday You're over 70" in str(exc.exception))

    def test_birthday_field_nullable_false(self):
        birthday_field_object = api.BirthDayField(required=True, field_name="birthday_field_object")
        with self.assertRaises(api.ValidationError):
            birthday_field_object.validate(None)

    def test_birthday_field_nullable_true(self):
        birthday_field_object = api.BirthDayField(required=True, nullable=True, field_name="birthday_field_object")
        birthday_field_object.validate(None)


class TestGenderField(unittest.TestCase):
    def test_gender_field_value(self):
        gender_field_object = api.GenderField(required=True)
        with self.assertRaises(api.ValidationError) as exc:
            gender_field_object.validate('gender')
        self.assertTrue("gender must be 0 or 1 or 2" in str(exc.exception))

    def test_gender_field_nullable_false(self):
        gender_field_object = api.GenderField(required=True)
        with self.assertRaises(api.ValidationError):
            gender_field_object.validate(None)

    def test_gender_field_nullable_true(self):
        gender_field_object = api.GenderField(required=True, nullable=True)
        gender_field_object.validate(None)


class TestArgumentsField(unittest.TestCase):
    def test_arguments_field_value(self):
        arguments_field_object = api.ArgumentsField(required=True)
        with self.assertRaises(api.ValidationError) as exc:
            arguments_field_object.validate('gender')
        self.assertTrue("arguments bad type <class 'str'>" in str(exc.exception))

    @staticmethod
    def error(data):
        raise json.JSONDecodeError(msg="error", doc="doc", pos=1)

    @uMock.patch('json.dumps')
    def test_arguments_field_value2(self, mock_obj):
        mock_obj.side_effect = self.error
        arguments_field_object = api.ArgumentsField(required=True)
        with self.assertRaises(api.ValidationError) as exc:
            arguments_field_object.validate({'date': 1})
        self.assertTrue("error: arguments JSONDecodeError" in str(exc.exception))

    def test_arguments_field_nullable_false(self):
        arguments_field_object = api.ArgumentsField(required=True)
        with self.assertRaises(api.ValidationError):
            arguments_field_object.validate(None)

    def test_arguments_field_nullable_true(self):
        arguments_field_object = api.ArgumentsField(required=True, nullable=True)
        arguments_field_object.validate(None)


class TestClientIDsField(unittest.TestCase):
    def test_client_ids_field_value(self):
        arguments_field_object = api.ClientIDsField(required=True)
        with self.assertRaises(api.ValidationError) as exc:
            arguments_field_object.validate('')
        self.assertTrue("error: client_ids not list" in str(exc.exception))

    def test_client_ids_field_value2(self):
        arguments_field_object = api.ClientIDsField(required=True)
        with self.assertRaises(api.ValidationError) as exc:
            arguments_field_object.validate([])
        self.assertTrue("error: client_ids is empty list" in str(exc.exception))

    def test_client_ids_field_value3(self):
        arguments_field_object = api.ClientIDsField(required=True)
        with self.assertRaises(api.ValidationError) as exc:
            arguments_field_object.validate(['a'])
        self.assertTrue("error: not number in client_ids" in str(exc.exception))

    def test_client_ids_field_nullable_false(self):
        arguments_field_object = api.ClientIDsField(required=True)
        with self.assertRaises(api.ValidationError):
            arguments_field_object.validate(None)

    def test_client_ids_field_nullable_true(self):
        arguments_field_object = api.ClientIDsField(required=True, nullable=True)
        arguments_field_object.validate(None)


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    unittest.main()
