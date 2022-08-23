from .. import demistomock as demisto
from ..CommonServerPython import *
from ..CommonServerUserPython import *

from typing import Dict, Any
import json
import datetime
from textwrap import indent
import yaml
import os

''' STANDALONE FUNCTION '''


def load_raw_list(xsoar_list: str):
    load_res = demisto.executeCommand('getList', {'listName': xsoar_list})
    if (
            not isinstance(load_res, list)
            or 'Contents' not in load_res[0]
            or not isinstance(load_res[0]['Contents'], str)
            or load_res[0]['Contents'] == 'Item not found (8)'
    ):
        raise ValueError(f'Cannot retrieve list {xsoar_list}')
    list_data: Dict = {}
    raw_data: str = load_res[0]['Contents']
    return raw_data


def load_json_list(xsoar_list: Any) -> Dict:
    raw_data = load_raw_list(xsoar_list)
    list_data: Dict = {}
    if raw_data and len(raw_data) > 0:
        try:
            list_data = json.loads(raw_data)
        except json.decoder.JSONDecodeError as e:
            raise ValueError(f'List does not contain valid JSON data: {e}')
    return list_data


def load_yaml_list(xsoar_list: str) -> Dict:
    raw_data = load_raw_list(xsoar_list)
    list_data: Dict = {}
    if raw_data and len(raw_data) > 0:
        try:
            list_data = yaml.load(raw_data, Loader=yaml.FullLoader)
        except yaml.YAMLError as err:
            raise ValueError(f'List does not contain valid YAML data: {err}')
    return list_data


def is_working_day(list_name: str = '') -> bool:
    days_of_week = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    work_week = load_yaml_list(list_name)
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


''' COMMAND FUNCTION '''


def modify_timer(args: Dict[str, Any]) -> Any:
    mapped_acts = {"start": "startTimer",
                   "stop": "stopTimer",
                   "pause": "pauseTimer"}
    list_name = args.get('xsoar_list', None)
    if not list_name:
        raise ValueError('xsoar_list not specified')
    old = args.get("old")
    new = args.get("new")
    # Check if it is a working day
    is_workday = is_working_day()
    config_dict = load_yaml_list(list_name)
    acts = config_dict.get(old).get('NextStages').get(new)
    actions_taken = []
    for act in acts:
        if act.get('weekdayOnly') and is_workday:
            action = mapped_acts.get(act.get('action'))
            timer = act.get('timerName')
            params = {"timerField": timer}
            demisto.executeCommand(action, params)
            action_taken = f'Action {action} taken on Timer: {timer}'
            actions_taken.append(action_taken)
        else:
            action = mapped_acts.get(act.get('action'))
            timer = act.get('timerName')
            params = {"timerField": timer}
            demisto.executeCommand(action, params)
            action_taken = f'Action {action} taken on Timer: {timer}'
            actions_taken.append(action_taken)
    return actions_taken


''' MAIN FUNCTION '''


def main():
    try:
        # TODO: replace the invoked command function with yours
        return_results(modify_timer(args=demisto.args()))
    except Exception as ex_str:
        return_error(f'Failed to execute Modify Timer On Stage Change. Error: {str(ex_str)}')


''' ENTRY POINT '''

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
