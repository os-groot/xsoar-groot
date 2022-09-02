import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
from CommonServerPython import __line__

register_module_line('TimeToEscalateWidget', 'start', __line__())
'''IMPORTS'''
from typing import Dict
import yaml
import traceback
import datetime
import math

'''GLOBALS'''
DEFAULT_FROM = '1 hour ago'
DEFAULT_TO = '1 minute ago'
EXTERNAL_TIMER = 'CustomFields.externalescalationsla'
TTE_TIMER = 'CustomFields.timetoescalate'
SLA_TIMER = 'CustomFields.remediationsla'
TZ = '+0300'
FIELDS = {'Incident Created': 'created', 'Incident ID': 'id', 'Incident Name': 'name',
          'Incident Type': 'type', 'Status': 'status',
          'Incident Stage': 'CustomFields.incidentstage', 'Owner': 'owner', 'Severity': 'severity',
          'Reason For Closure': 'closeReason', 'Kill Chain Stage': 'CustomFields.killchainstage',
          'Incident Duration': 'openDuration', 'Acknowledged Time': 'CustomFields.incidentacknowledgementdate'
          }
DISPLAYED_TIME_FIELDS = ['Incident Created', 'Acknowledged Time']
QUERY_SIZE = 5000
SORT_FIELD = 'created'
ESCALATION_STAGE = 'External Escalation'

'''STAND ALONE FUNCTIONS'''


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


def check_sla(timer=None, sla=None, duration=None) -> str:
    if sla is None:
        timer_sla = timer.get('sla', 0)
    else:
        timer_sla = sla
    if duration is None:
        timer_duration = timer.get('totalDuration') / 60
    else:
        timer_duration = duration
    if timer_sla >= timer_duration > 0:
        sla_verdict = 'SLA Met'
    elif timer_sla < timer_duration:
        sla_verdict = 'SLA Breach'
    else:
        sla_verdict = f'Uncomputed, SLA: {timer_sla}'
    return sla_verdict


# noinspection DuplicatedCode
def str_date_parser(str_date, local_tz='+0300', to_tz=TZ,
                    return_date_time=False, is_utc=False, readable=True) -> Union[str, datetime.datetime]:
    if isinstance(str_date, datetime.datetime):  # Stop Process if received a Date Time Object
        return str_date
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
    # Set Default Times
    now = datetime.datetime.now(timezone.utc)
    default_time = now + timedelta(minutes=int(99))
    default_time = default_time.isoformat()
    default_now = now
    default_now = default_now.isoformat()
    # Extract times form incident
    escalation_timer: dict = demisto.get(incident, EXTERNAL_TIMER)
    escalation_timer_sla = escalation_timer.get('sla', 30)  # SLA allocation in Minutes
    escalation_timer_duration: int = demisto.get(escalation_timer, 'totalDuration', defaultParam=0)  # Seconds
    escalation_timer_start = demisto.get(escalation_timer, 'startDate')  # Start Date of Escalation Timer
    escalation_timer_start = str_date_parser(escalation_timer_start, return_date_time=True)
    tte_timer: dict = demisto.get(incident, TTE_TIMER)  # Time to escalate timer
    tte_timer_sla = tte_timer.get('sla', 30)  # SLA allocation in Minutes
    # Creation date of incident in XSOAR
    created_time = str_date_parser(demisto.get(incident, 'created'), return_date_time=True)
    sla_timer = demisto.get(incident, SLA_TIMER)
    sla_timer_duration: int = demisto.get(sla_timer, 'totalDuration', defaultParam=0)  # Seconds
    sla_paused_duration: int = demisto.get(sla_timer, 'accumulatedPause')  # Seconds
    '''Time to escalation is computed as TTE = ("Escalation date" - "Creation Date") - "Total Paused Duration" '''
    event_end = inc_custom.get('detectedtime')
    # Compute ("Escalation date" - "Creation Date")
    time_to_escalation = (escalation_timer_start - created_time) - datetime.timedelta(seconds=sla_paused_duration)
    time_to_escalation_secs = time_to_escalation.total_seconds()
    time_to_escalation_readable = sec_to_readable(time_to_escalation.total_seconds())
    # Set row values
    display_inc['Time To Escalation'] = time_to_escalation_readable
    display_inc['Required SLA'] = sec_to_readable(tte_timer_sla * 60)  # Readable time from seconds
    display_inc['SLA Verdict'] = check_sla(sla=int(tte_timer_sla*60), duration=int(time_to_escalation_secs))
    display_inc['Escalation Date'] = readable_time(escalation_timer_start)
    display_inc['Severity'] = severity_map(display_inc['Severity'])
    return display_inc


# noinspection DuplicatedCode
''' COMMAND FUNCTION '''


def build_table(args):
    from_date_arg = args.get('from', DEFAULT_FROM)
    from_date = str_date_parser(str_date=from_date_arg, to_tz=TZ)
    to_date_arg = args.get('to', DEFAULT_TO)
    to_date = str_date_parser(str_date=to_date_arg, to_tz=TZ)
    query = args_to_string(args, 'searchQuery')
    if query is None or query == '' or query == str(None):
        final_query = f'(created:>="{from_date}"  and created:<="{to_date}") and incidentstage:"{ESCALATION_STAGE}"'
    elif query is not None and f'incidentstage:"{ESCALATION_STAGE}"' in query:
        time_query = f'(created:>="{from_date}" and created:<="{to_date}")'
        final_query = f'({query}) and {time_query}'
    else:
        time_query = f'(created:>="{from_date}" and created:<="{to_date}")'
        final_query = f'incidentstage:"{ESCALATION_STAGE}" and ({query}) and {time_query}'
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
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute TimeToEscalateWidget. Error: {traceback.format_exc()}')


''' ENTRY POINT '''

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
register_module_line('TimeToEscalateWidget', 'end', __line__())
