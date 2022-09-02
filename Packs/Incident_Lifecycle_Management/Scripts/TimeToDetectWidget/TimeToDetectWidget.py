import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
from CommonServerPython import __line__

register_module_line('TimeToDetectWidget', 'start', __line__())
'''IMPORTS'''
from typing import Dict
import yaml
import traceback
import datetime as dtime
import math
import sys
import os
import dateutil.parser as du
import dateutil.tz as tz

'''GLOBALS'''
DEFAULT_FROM = '1 hour ago'
DEFAULT_TO = '1 minute ago'
DETECTION_TIMER = 'CustomFields.detectionsla'
EVENT_TIME_FIELD = 'CustomFields.eventtimes'
TZ = '+0300'
FIELDS = {'Incident Created': 'created', 'Incident ID': 'id', 'Incident Name': 'name',
          'Source': 'sourceInstance', 'Severity': 'severity', 'Splunk Search Time': 'CustomFields.splunksearchtime'
          }
DISPLAYED_TIME_FIELDS = ['Incident Created', 'Splunk Search Time']
QUERY_SIZE = 5000
SORT_FIELD = 'created'

'''STAND ALONE FUNCTIONS'''


def readable_time(a_time):
    if a_time is None:
        return 'Empty'
    if isinstance(a_time, dtime.datetime):
        a_time = a_time.isoformat()
    if isinstance(a_time, str):
        a_time = a_time.strip()
    if isinstance(a_time, (float, int)):
        a_time = str(a_time)
    parser_settings = {'TIMEZONE': TZ, 'TO_TIMEZONE': TZ, 'RETURN_AS_TIMEZONE_AWARE': True}
    str_date_parsed = dateparser.parse(a_time, settings=parser_settings)  # Convert to DateTime
    readable = str_date_parsed.isoformat(timespec="seconds")
    ret_time = readable
    return ret_time


def sec_to_readable(secs=0, time_delta=True):
    formatted = time.strftime("%H:%M:%S", time.gmtime(secs))
    if time_delta:
        hrs = secs // 3600
        mins = (secs % 3600) // 60
        seconds = secs % 60
        formatted = '{}:{}:{}'.format(int(hrs), int(mins), int(seconds))
        # formatted = str(datetime.timedelta(seconds=secs))
    return formatted


# noinspection DuplicatedCode
def severity_map(sev):
    if sev is None:
        return 'Unknown'
    severities_list = ['Unknown', 'Informational', 'Low', 'Medium', 'High', 'Critical']
    if str(sev) in severities_list:
        return str(sev)
    if isinstance(sev, int):
        sev = str(sev)
    severities = {'0': 'Informational', '1': 'Low', '2': 'Medium', '3': 'High', '4': 'Critical'}
    sev = severities.get(sev)
    return sev


# noinspection DuplicatedCode
def split_lines(to_split):
    if isinstance(to_split, list) and len(to_split) == 1:
        the_str = to_split[0]
    elif isinstance(to_split, list) and len(to_split) > 1:
        return to_split
    the_str = to_split
    res = str(the_str).splitlines()
    if res is None or len(res) <= 0:
        res = []
    return res


# noinspection DuplicatedCode
def format_date_fields(display_inc):
    for t_field in DISPLAYED_TIME_FIELDS:
        if t_field not in list(FIELDS.keys()):
            continue
        t_val = display_inc[t_field]
        if t_val == 'Empty' or t_val == "" or t_val is None or t_val == str(None):
            continue
        t_val = str_date_parser(t_val)
        display_inc[t_field] = t_val
    return display_inc


# noinspection DuplicatedCode
def set_columns(incident, fields_map=None):
    if fields_map is None:
        fields_map = FIELDS
    display_inc = {k: demisto.get(incident, str(v), defaultParam='Empty') for k, v in FIELDS.items()}
    display_inc = format_date_fields(display_inc)  # Make Each Displayed time field more human-readable
    inc_custom = demisto.get(incident, 'CustomFields')
    labels = demisto.get(incident, 'labels')
    labels = {d['type']: d['value'] for d in labels}
    detection_timer = demisto.get(incident, DETECTION_TIMER)
    detection_timer_sla = detection_timer.get('sla', 30)  # Allocated SLA in minutes
    xsoar_created_time = demisto.get(incident, 'created')  # Creation date of incident in XSOAR
    xsoar_created_time = str_date_parser(xsoar_created_time, return_date_time=True)  # Creation date of incident in XSOAR
    # now = dtime.datetime.now(timezone.utc)
    # Calculate Event End
    # default_time = now + timedelta(minutes=int(60))
    # default_time = default_time.isoformat()
    # default_now = now
    # default_now = default_now.isoformat(timespec="seconds")
    # event_times = demisto.get(incident, EVENT_TIME_FIELD)
    # event_times = split_lines(event_times)
    # if event_times is not None and len(event_times) > 0 and event_times != "[]":
    #     try:
    #         event_times = [str_date_parser(e_time, to_tz=TZ, return_date_time=True)
    #                        for e_time in event_times if e_time is not None
    #                        and str(e_time) != str(None) and e_time != "" and e_time != "[]"]
    #     except Exception:
    #         tb = traceback.format_exc()
    #         return_error(f'Failed to execute TimeToEscalateWidget. Error: {tb}')
    #     event_times = sorted(event_times)
    #     event_end = event_times[-1] if len(event_times) > 0 else None
    # else:
    #     event_end = default_now
    # # Handle failed Calculate Event End Time
    # if event_end is None or str(event_end) == '' or str(event_end) == str(None) \
    #         or str(event_end) == str(default_now):
    #     event_end = default_now
    #     display_inc['Events End Time'] = f'(Default): {event_end}'
    # else:
    #     if isinstance(event_end, dtime.datetime):
    #         event_end = event_end.isoformat()
    #     display_inc['Events End Time'] = event_end
    # event_end = str_date_parser(str(event_end), to_tz=TZ)
    # event_end = dtime.datetime.fromisoformat(event_end)
    # Get Splunk Search Time
    info_search_time = labels.get('info_search_time')
    info_search_time = int(float(info_search_time)) if info_search_time is not None else ''
    used_splunk_info_search_time = False
    used_xsoar_created_time = False
    search_time = inc_custom.get('splunksearchtime')
    if isinstance(search_time, (float, int)):
        search_time = str_date_parser(search_time, return_date_time=True)
    if search_time is None or str(search_time) == '' or str(search_time) == str(None):
        if info_search_time != '':
            search_time = info_search_time
            used_splunk_info_search_time = True
            if isinstance(search_time, (float, int)):
                search_time = str_date_parser(search_time, return_date_time=True, local_tz='utc')
            display_inc['Splunk Search Time'] = 'used info_search_time'
        else:
            display_inc['Splunk Search Time'] = 'Empty'
            search_time = xsoar_created_time
            used_xsoar_created_time = True
    elif used_splunk_info_search_time:
        display_inc['Splunk Search Time'] = 'used info_search_time'
        search_time = str_date_parser(search_time, to_tz=TZ, return_date_time=True)
    else:
        display_inc['Splunk Search Time'] = readable_time(search_time)
        search_time = str_date_parser(search_time, to_tz=TZ, return_date_time=True)
    # Get Detected time
    # detection_time = inc_custom.get('detectedtime')
    if used_xsoar_created_time:
        detection_time = xsoar_created_time
        display_inc['Detection Time'] = f'XSOAR Created Time: {readable_time(detection_time)}'
    elif used_splunk_info_search_time:
        detection_time = search_time
        display_inc['Detection Time'] = f'Splunk info_search Time: {readable_time(detection_time)}'
    else:
        detection_time = search_time
        display_inc['Detection Time'] = f'{readable_time(detection_time)}'
    '''Time to escalation is computed as TTD = ("Creation Date" - "Security Control Time(detectedtime)")'''
    time_diff = xsoar_created_time - detection_time
    time_diff_minutes = time_diff.total_seconds() / 60
    if detection_timer_sla >= time_diff_minutes >= 0:
        sla_verdict = 'SLA Met'
    elif detection_timer_sla < time_diff_minutes:
        sla_verdict = 'SLA Breach'
    else:
        sla_verdict = 'Uncomputed'
    # time_diff_minutes = math.ceil(time_diff_minutes)
    display_inc['Time Consumed To Detect HH:MM:SS'] = sec_to_readable(int(time_diff_minutes*60))
    display_inc['SLA Verdict'] = sla_verdict
    display_inc['Severity'] = severity_map(display_inc['Severity'])
    return display_inc


# noinspection DuplicatedCode
def str_date_parser(str_date, local_tz='+0300', to_tz=TZ,
                    return_date_time=False, is_utc=False, readable=True) -> Union[str, datetime]:
    if isinstance(str_date, datetime):  # Stop Process if received a Date Time Object
        return str_date
    if isinstance(str_date, (float, int)):
        str_date = str(str_date)
    str_date = arg_to_datetime(str_date.strip(), is_utc=is_utc)  # Convert String to DateTime
    parser_settings = settings = {'TIMEZONE': local_tz, 'TO_TIMEZONE': to_tz,
                                  'RETURN_AS_TIMEZONE_AWARE': True}
    str_date_parsed = dateparser.parse(str_date.isoformat(), settings=parser_settings)
    if return_date_time:
        return str_date_parsed
    elif readable:
        return str_date_parsed.isoformat(timespec="seconds")
    else:
        return str_date_parsed.isoformat()


def args_to_string(args: Dict, arg_name: str) -> str:
    arg_name = arg_name.strip()
    args = args.get(arg_name, None)
    if not args:
        return str(None)
    else:
        stripped_arg = str(args).strip()
        return stripped_arg


# noinspection DuplicatedCode
''' COMMAND FUNCTION '''


def build_table(args):
    from_date_arg = args.get('from', DEFAULT_FROM)
    from_date = str_date_parser(str_date=from_date_arg, to_tz=TZ)
    to_date_arg = args.get('to', DEFAULT_TO)
    to_date = str_date_parser(str_date=to_date_arg, to_tz=TZ)
    query = args_to_string(args, 'searchQuery')
    if query is None or query == '' or query == str(None):
        final_query = f'(created:>="{from_date}"  and created:<="{to_date}")'
    else:
        final_query = f'{query} and (created:>="{from_date}"  and created:<="{to_date}")'
    table = TableOrListWidget()
    command_args = {'query': final_query}
    args = {"query": final_query, "size": QUERY_SIZE, "sort": f"{SORT_FIELD}.desc"}
    incidents_query_res = demisto.executeCommand('getIncidents', args)[0]
    count = demisto.get(incidents_query_res, 'Contents.total')
    incidents = demisto.get(incidents_query_res, 'Contents.data')
    # incidents = pd.json_normalize(incidents, sep='-').to_dict(orient='records')
    if not incidents:
        print(f'No Results for query: {final_query}')
        return [{'Query': final_query}]
    else:
        for inc in incidents:
            display_row = set_columns(inc, FIELDS)
            table.add_row(display_row)
        return table


def main():
    try:
        args: dict = demisto.args()
        return_results(build_table(args))
    except Exception:
        tb = traceback.format_exc()
        # demisto.error(e)  # print the traceback
        return_error(f'Failed to execute TimeToEscalateWidget. Error: {tb}')


''' ENTRY POINT '''

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
register_module_line('TimeToDetectWidget', 'end', __line__())
