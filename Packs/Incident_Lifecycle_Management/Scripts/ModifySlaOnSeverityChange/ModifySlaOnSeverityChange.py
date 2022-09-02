from CommonServerPython import __line__
import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

register_module_line('ModifySLAOnSeverityChange', 'start', __line__())
'''IMPORTS'''
from typing import Dict, Any
import yaml
import dateparser
from datetime import datetime

'''GLOBALS'''
LIST_TYPE: str = r'JSON'
LIST_NAME: str = r'Timers-SLA-By-Severity'

''' STANDALONE FUNCTION '''


def str_to_iso_format_utc(str_date, local_tz='+0300', to_tz='UTC',
                          return_date_time=False, is_utc=False) -> Union[str, Any]:
    str_date = arg_to_datetime(str_date.strip(), is_utc=is_utc)  # Convert String to DateTime
    parser_settings = settings = {'TIMEZONE': local_tz, 'TO_TIMEZONE': to_tz,
                                  'RETURN_AS_TIMEZONE_AWARE': True}
    str_date_parsed = dateparser.parse(str_date.isoformat(), settings=parser_settings)
    if return_date_time:
        return str_date_parsed
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


def load_list(xsoar_list: str) -> Union[Dict, str]:
    load_res = demisto.executeCommand('getList', {'listName': xsoar_list})
    if (
            not isinstance(load_res, list)
            or 'Contents' not in load_res[0]
            or not isinstance(load_res[0]['Contents'], str)
            or load_res[0]['Contents'] == 'Item not found (8)'
    ):
        raise ValueError(f'Cannot retrieve list {xsoar_list}')
    raw_data: str = load_res[0]['Contents']
    list_data: Dict = {}
    if raw_data and len(raw_data) > 0 and LIST_TYPE == r'JSON':
        try:
            list_data = json.loads(raw_data)
        except json.decoder.JSONDecodeError as e:
            raise ValueError(f'List does not contain valid JSON data: {e}')
        # print(f'JSON: {list_data}')
        return list_data
    elif raw_data and len(raw_data) > 0 and LIST_TYPE == 'YAML':
        try:
            list_data = yaml.load(raw_data, Loader=yaml.FullLoader)
        except yaml.YAMLError as err:
            raise ValueError(f'List does not contain valid YAML data: {err}')
        # print(f'YAML: {list_data}')
        return list_data
    else:
        # print(f'Raw: {raw_data}')
        return raw_data


''' COMMAND FUNCTION '''


# noinspection DuplicatedCode
def modify_sla(args: Dict):
    list_name = LIST_NAME
    old: str = args_to_string(args, 'old')
    new: str = args_to_string(args, 'new')
    if str(new) in ['Unknown', 'Informational', 'Low', 'Medium', 'High', 'Critical']:
        severity_map = {'Low': 'P4', 'Medium': 'P3', 'High': 'P2', 'Critical': 'P1'}
    else:
        severity_map = {'1': 'P4', '2': 'P3', '3': 'P2', '4': 'P1'}
    config_dict = load_list(list_name)
    inc = demisto.incident()
    actions_taken = []
    for timer_conf in config_dict:
        timer_conf = config_dict.get(timer_conf)
        severity: str = severity_map.get(new)
        # print(f'Severity: {new}')
        # print(f'Severity MAP: {severity}')
        sla = timer_conf.get(severity)
        sla = sla  # Get SLA in minutes for the severity for this timer
        cli_name = timer_conf.get("cli")
        timer = demisto.get(inc, f'CustomFields.{cli_name}', defaultParam='Empty')
        due_date = timer.get('dueDate')
        run_status = demisto.get(timer, 'runStatus')
        parser_settings = settings = {'TIMEZONE': 'utc', 'RETURN_AS_TIMEZONE_AWARE': True}
        if str(run_status) not in ['idle', 'ended']:
            # # due_date = due_date
            # # due_date: str = str_to_iso_format_utc(str_date=due_date, return_date_time=False)
            # # curr_due = datetime.fromisoformat(due_date)
            # # sla_due = curr_due + timedelta(minutes=sla)
            # sla_due = sla_due.isoformat()
            params = {'sla': sla, 'slaField': cli_name}
            demisto.executeCommand('setIncident', params)
            action_taken = f'Set Timer: {cli_name} SLA to: {sla} minutes from now IF it was running'
            actions_taken.append(action_taken)
        if str(run_status) == 'idle':
            now = datetime.now(timezone.utc)
            sla_due = now + timedelta(minutes=sla)
            sla_due = sla_due.isoformat()
            params = {'sla': sla, 'slaField': cli_name}
            demisto.executeCommand('setIncident', params)
            action_taken = f'Set Timer: {cli_name} SLA to: {sla} minutes from now IF it was running'
            actions_taken.append(action_taken)
    return actions_taken


''' MAIN FUNCTION '''


def main():
    try:
        return_results(modify_sla(demisto.args()))
    except Exception as ex_str:
        print(traceback.format_exc())
        traceback.print_exc()
        # return_error(f'Failed to execute Modify SLA On Severity Change. Error: {str(ex_str)}')


''' ENTRY POINT '''

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
register_module_line('ModifySLAOnSeverityChange', 'end', __line__())
