from CommonServerPython import __line__
from .. import demistomock as demisto, CommonServerPython
from ..CommonServerPython import *
from ..CommonServerUserPython import *

register_module_line('ModifyTimerOnStageChange', 'start', __line__())
from typing import Dict, Any
import json
import datetime
import yaml

# import os
# from textwrap import indent

'''GLOBALS'''
LIST_TYPE: str = ''

''' STANDALONE FUNCTION '''


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
    if raw_data and len(raw_data) > 0 and LIST_TYPE == 'JSON':
        try:
            list_data = json.loads(raw_data)
        except json.decoder.JSONDecodeError as e:
            raise ValueError(f'List does not contain valid JSON data: {e}')
        return list_data
    elif raw_data and len(raw_data) > 0 and LIST_TYPE == 'YAML':
        try:
            list_data = yaml.load(raw_data, Loader=yaml.FullLoader)
        except yaml.YAMLError as err:
            raise ValueError(f'List does not contain valid YAML data: {err}')
        return list_data
    else:
        return raw_data


def is_working_day(list_name: str = '') -> bool:
    days_of_week = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    work_week = load_list(list_name)
    start_day = str(work_week.get('StartDay')).lower()
    start_day = days_of_week.index(start_day)
    last_day = str(work_week.get('LastDay')).lower()
    last_day = days_of_week.index(last_day)
    start_time = work_week.get('StartTime')
    stop_time = work_week.get('StopTime')
    now = datetime.now(timezone.utc)
    today = days_of_week[now.weekday()]
    # if today:
    #     print()
    # Determine if it's a weekday by checking for on call users, on call users are determined by Shifts defined on role
    get_users_response: List = demisto.executeCommand('getUsers', {'onCall': True})
    if is_error(get_users_response):
        demisto.error(f'Failed to get users on call: {str(get_error(get_users_response))}')
    else:
        contents = get_users_response[0]
        if contents == 'No data returned':
            contents = 'On-Call Team members\nNo team members were found on-call.'
            return_results(contents)
            is_weekday = False
            return is_weekday
        else:
            is_weekday = True
            return is_weekday


def check_next_stage(old, new, config_dict: Dict) -> bool:
    next_stages = config_dict.get(old).get('NextStages').keys()
    if new in next_stages:
        return True
    else:
        return False


def args_to_string(args: Dict, arg_name: str) -> str:
    arg_name = arg_name.strip()
    args = args.get(arg_name, None)
    if not args:
        return str(None)
    stripped_arg = str().strip()
    return stripped_arg


''' COMMAND FUNCTION '''


def modify_timer(args: Dict[str, Any]) -> Any:
    mapped_acts = {"start": "startTimer",
                   "stop": "stopTimer",
                   "pause": "pauseTimer"}
    list_name = args_to_string(args, 'xsoar-list')
    if not list_name:
        raise ValueError('xsoar_list not specified')
    old: str = args_to_string(args, 'old')
    new: str = args_to_string(args, 'new')
    config_dict = load_list(list_name)
    # Return Error if new stage is not in allowed Next Stages
    if not check_next_stage(old=old, new=new, config_dict=config_dict):
        next_stages = config_dict.get(old).get('NextStages').keys()
        err_str = f'Moving From Stage: {old} to Stage: {new} is not allowed. Allowed stages are: {next_stages}'
        return_error(error=err_str, message=err_str)
    # Take action on timers
    is_workday = is_working_day()  # Check if it is a working day
    acts = config_dict.get(old).get('NextStages').get(new)
    actions_taken = []
    for act in acts:
        if act.get('weekdayOnly') and is_workday:
            xsoar_command = mapped_acts.get(act.get('action'))
            timer = act.get('timerName')
            params = {"timerField": timer}
            demisto.executeCommand(xsoar_command, params)
            action_taken = f'Action {xsoar_command} taken on Timer: {timer}'
            actions_taken.append(action_taken)
        else:
            xsoar_command = mapped_acts.get(act.get('action'))
            timer = act.get('timerName')
            params = {"timerField": timer}
            demisto.executeCommand(xsoar_command, params)
            action_taken = f'Action {xsoar_command} taken on Timer: {timer}'
            actions_taken.append(action_taken)
    return actions_taken


''' MAIN FUNCTION '''


def main():
    try:
        global LIST_TYPE
        LIST_TYPE = args_to_string(demisto.args(), 'type')
        # TODO: replace the invoked command function with yours
        return_results(modify_timer(args=demisto.args()))
    except Exception as ex_str:
        return_error(f'Failed to execute Modify Timer On Stage Change. Error: {str(ex_str)}')


''' ENTRY POINT '''

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
register_module_line('ModifyTimerOnStageChange', 'end', __line__())
