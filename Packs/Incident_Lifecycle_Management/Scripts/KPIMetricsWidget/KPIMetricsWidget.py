import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
from CommonServerPython import __line__

# from ..CommonServerUserPython import *
register_module_line('KPIMetricsWidget', 'start', __line__())
'''IMPORTS'''
from typing import Dict
import yaml
import traceback
import datetime
import math
import sys
import os

'''GLOBALS'''
DEFAULT_FROM = '1 hour ago'
DEFAULT_TO = '1 minute ago'
SLA_TIMER = 'CustomFields.remediationsla'
EVENT_TIME_FIELD = 'CustomFields.eventtimes'
TZ = '+0300'
FIELDS = {'Incident Created': 'created', 'Incident ID': 'id', 'Incident Name': 'name',
          'Incident Stage': 'CustomFields.incidentstage', 'Owner': 'owner', 'Severity': 'severity',
          'Reason For Closure': 'closeReason', 'Kill Chain Stage': 'CustomFields.killchainstage',
          'Detected Time - Splunk': 'CustomFields.detectedtime', 'Incident Duration': 'openDuration',
          'Acknowledged Time': 'CustomFields.incidentacknowledgementdate'
          }
DISPLAYED_TIME_FIELDS = ['Incident Created', 'Detected Time - Splunk']
QUERY_SIZE = 5000
SORT_FIELD = 'created'

'''STANDALONE FUNCTIONS'''


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


def readable_time(a_time):
    if isinstance(a_time, str):
        a_time = datetime.datetime.fromisoformat(a_time)
    ret_time = a_time.isoformat(timespec="seconds")
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


def check_sla(timer) -> str:
    timer_sla = timer.get('sla', 0)
    timer_duration = timer.get('totalDuration')/60
    if timer_sla >= timer_duration > 0:
        sla_verdict = 'SLA Met'
    elif timer_sla < timer_duration:
        sla_verdict = 'SLA Breach'
    else:
        sla_verdict = f'Uncomputed, SLA: {timer_sla}'
    return sla_verdict


def set_columns(incident, fields_map=None):
    if fields_map is None:
        fields_map = FIELDS
    display_inc = {k: demisto.get(incident, str(v), defaultParam='Empty') for k, v in FIELDS.items()}
    # Make Each Displayed time field more human-readable
    for t_field in DISPLAYED_TIME_FIELDS:
        t_val = display_inc[t_field]
        if t_val == 'Empty' or t_val == "" or t_val is None or t_val == str(None):
            # display_inc[f'R - {t_field}'] = t_val
            continue
        t_val = str_date_parser(t_val)
        display_inc[t_field] = t_val
    inc_custom = demisto.get(incident, 'CustomFields')
    sla_timer = demisto.get(incident, SLA_TIMER)
    sla_timer_duration: int = demisto.get(sla_timer, 'totalDuration', defaultParam=0)  # Seconds
    sla_time_allocated = demisto.get(sla_timer, 'sla')  # Minutes
    sla_time_allocated = sec_to_readable(sla_time_allocated * 60)
    sla_duration_readable: str = sec_to_readable(sla_timer_duration)
    display_inc['Time To Response'] = sla_duration_readable
    display_inc['Required SLA'] = sla_time_allocated
    display_inc['SLA Verdict'] = check_sla(sla_timer)
    display_inc['Severity'] = severity_map(display_inc['Severity'])
    return display_inc


# noinspection DuplicatedCode
def str_date_parser(str_date, local_tz='+0300', to_tz=TZ,
                    return_date_time=False, is_utc=False, readable=True) -> Union[str, datetime.datetime]:
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
register_module_line('KPIMetricsWidget', 'end', __line__())
