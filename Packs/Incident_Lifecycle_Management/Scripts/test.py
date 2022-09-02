# def get_value():
#     return input('Put Number').strip()
#
#
# if tmp := get_value():
#     x = tmp
# print(x)

from CommonServerPython import *
import datetime
import dateparser

TZ = '+0300'


def str_date_parser(str_date, local_tz='+0300', to_tz=TZ,
                    return_date_time=False, is_utc=False, readable=True):
    if isinstance(str_date, datetime.datetime):  # Stop Process if received a Date Time Object
        return str_date
    str_date = str_date.strip()  # Convert String to DateTime
    parser_settings = {'TIMEZONE': local_tz, 'TO_TIMEZONE': to_tz, 'RETURN_AS_TIMEZONE_AWARE': True}
    str_date_parsed = dateparser.parse(str_date, settings=parser_settings)
    if return_date_time:
        return str_date_parsed
    elif readable:
        return str_date_parsed.isoformat(timespec="seconds")
    else:
        return str_date_parsed.isoformat()


import dateutil.parser as du
while (i := input("Enter Time: ")) != 'quit':
    # t = str_date_parser(i)
    t = arg_to_datetime(i)
    print(t)

