import base64
import binascii
import datetime

def is_base64(string: str) -> bool:
    try:
        base64.b64decode(string, validate=True)
    except binascii.Error:
        return False
    else:
        return True

def get_datetime_from_timestamp(timestamp: int) -> datetime.datetime:
    try:
        dt = datetime.datetime.utcfromtimestamp(timestamp)
    except ValueError:
        dt = datetime.datetime.utcfromtimestamp(timestamp // 1000)
    return dt
