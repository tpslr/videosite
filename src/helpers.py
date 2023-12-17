from functools import wraps
from flask import request


# decorator to wrap a request function with, makes sure form data exists and is the right type
def requires_form_data(values: dict[str, type]):
    def _requires_form_data(f):
        @wraps(f)
        def __requires_form_data(*args, **kwargs):
            for name, v_type in values.items():
                if name not in request.form:
                    # value missing from form data
                    return create_error(f"Form data is missing \"{name}\"")
                try:
                    # try to cast the value to the type specified (to confirm it can be done)
                    v_type(request.form[name])
                except:
                    return create_error(f"Form data is invalid, \"{name}\" should be \"{str(v_type)}\"")

            return f(*args, **kwargs)
        return __requires_form_data
    return _requires_form_data


def create_error(message: str):
    return { "error": { "message": message } }
