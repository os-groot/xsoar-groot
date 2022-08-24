# from .. import demistomock as demisto
from CommonServerPython import __line__
from ..CommonServerPython import *

# from ..CommonServerUserPython import *
register_module_line('ModifyStageOnAssignment', 'start', __line__())
from typing import Dict

''' STANDALONE FUNCTION '''


def args_to_string(args: Dict, arg_name: str) -> str:
    arg_name = arg_name.strip()
    args = args.get(arg_name, None)
    if not args:
        return str(None)
    stripped_arg = str().strip()
    return stripped_arg


''' COMMAND FUNCTION '''


def modify_stage(args: Dict):
    old: str = args_to_string(args, 'old')
    new: str = args_to_string(args, 'new')
    acknowledgment_stage: str = args_to_string(args, 'acknowledgment-stage')
    if old == '' and new != '':
        params = {'incidentstage': acknowledgment_stage}
        demisto.executeCommand('setIncident', args=params)
    action_taken = f'Set Incident Stage to: {acknowledgment_stage} with owner: {new}'
    return action_taken


''' MAIN FUNCTION '''


def main():
    try:
        # TODO: replace the invoked command function with yours
        args = demisto.args()
        return_results(modify_stage(args=args))
    except Exception as ex_str:

        return_error(f'Failed to execute Modify Stage On Assignment. Error: {str(ex_str)}')


''' ENTRY POINT '''

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
register_module_line('ModifyStageOnAssignment', 'end', __line__())
