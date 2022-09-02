# from .. import demistomock as demisto
from CommonServerPython import __line__
from CommonServerPython import *

# from ..CommonServerUserPython import *
register_module_line('ModifyStageOnAssignment', 'start', __line__())
'''IMPORTS'''
from typing import Dict
import yaml
import traceback
import datetime

'''GLOBALS'''
# noinspection DuplicatedCode
PRE_ACKNOWLEDGMENT_STAGE = r'Queued'
ACKNOWLEDGMENT_STAGE = r'Initial'
ACKNOWLEDGMENT_FIELD = r'incidentacknowledgementdate'
TZ = '+0300'
LIST_TYPE: str = r'YAML'
LIST_NAME: str = r'IncidentStageManagement'

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


def args_to_string(args: Dict, arg_name: str) -> str:
    arg_name = arg_name.strip()
    args = args.get(arg_name, None)
    if not args:
        return str(None)
    else:
        stripped_arg = str(args).strip()
        return stripped_arg


# noinspection DuplicatedCode
def is_working_day(list_name: str = '') -> bool:
    days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    work_week = load_list(list_name)
    work_week = demisto.get(work_week, 'WorkWeek')
    start_day = str(work_week.get('StartDay')).lower()
    start_day = days_of_week.index(start_day)
    last_day = str(work_week.get('LastDay')).lower()
    last_day = days_of_week.index(last_day)
    start_time = work_week.get('StartTime')
    stop_time = work_week.get('StopTime')
    now = datetime.datetime.now(timezone.utc)
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


'''ACTION FUNCTIONS'''


# noinspection DuplicatedCode
def modify_timer(args: Dict[str, Any]) -> Any:
    mapped_acts = {"start": "startTimer",
                   "stop": "stopTimer",
                   "pause": "pauseTimer"}
    list_name = LIST_NAME
    if not list_name:
        raise ValueError('xsoar list not specified')
    config_dict = load_list(list_name)
    # Take action on timers
    is_workday = is_working_day(list_name)  # Check if it is a working day
    acts = config_dict.get(PRE_ACKNOWLEDGMENT_STAGE).get('NextStages').get(ACKNOWLEDGMENT_STAGE)
    actions_taken = []
    inc = demisto.incident()
    for act in acts:
        if act.get('weekdayOnly') and is_workday:
            xsoar_command = mapped_acts.get(act.get('action'))
            timer = act.get('timerName')
            command_params = {"timerField": timer}
            demisto.executeCommand(xsoar_command, command_params)
            action_taken = f'Action {xsoar_command} taken on Timer: {timer}'
            actions_taken.append(action_taken)
        else:
            xsoar_command = mapped_acts.get(act.get('action'))
            timer = act.get('timerName')
            command_params = {"timerField": timer}
            demisto.executeCommand(xsoar_command, command_params)
            action_taken = f'Action {xsoar_command} taken on Timer: {timer}'
            actions_taken.append(action_taken)
    return actions_taken


def modify_fields():
    now = datetime.datetime.now(timezone.utc)
    now_iso = now.isoformat()
    now_iso = str_to_iso_format_utc(str_date=now_iso, to_tz=TZ)
    command_params = {ACKNOWLEDGMENT_FIELD: now_iso}
    execute_command('setIncident', args=command_params)
    action_taken = f'Incident Acknowledged on: {now_iso}'
    additional_actions = [action_taken]
    return additional_actions


''' COMMAND FUNCTION '''


def modify_stage(args: Dict):
    old: str = args_to_string(args, 'old')
    new: str = args_to_string(args, 'new')
    acknowledgment_stage: str = ACKNOWLEDGMENT_STAGE
    if (old == '' or old == 'None' or old is None) and (new != '' and new is not None and new != 'None'):
        params = {'incidentstage': acknowledgment_stage}
        execute_command('setIncident', args=params)
        action_taken = f'Set Incident Stage to: {acknowledgment_stage} with owner: {new}'
        additional_actions = [action_taken] + modify_timer(args)
        additional_actions += modify_fields()
    else:
        action_taken = f'No Action Taken Owner Changed To: {new} From: {old}'
        additional_actions = [action_taken]
    return additional_actions


''' MAIN FUNCTION '''


def main():
    try:
        # TODO: replace the invoked command function with yours
        args = demisto.args()
        return_results(modify_stage(args=args))
    except Exception as ex_str:
        print(traceback.format_exc())
        traceback.print_exc()
    # return_error(f'Failed to execute Modify Stage On Assignment. Error: {str(ex_str)}')


''' ENTRY POINT '''

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
register_module_line('ModifyStageOnAssignment', 'end', __line__())
