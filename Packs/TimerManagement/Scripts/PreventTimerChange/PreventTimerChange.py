import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

from typing import Dict, Any

''' MAIN FUNCTION '''


def main():
    try:
        args = demisto.args()
        old = args.get("old")
        new = args.get("new")
        timer = args.get("cliName")
        timer_name = args.get("name")
        user = args.get("user")
        if user:
            name = user.get("name")
            if re.search("running", old):
                demisto.executeCommand("startTimer", {"timerField": timer})
                err_str = f"Invalid Timer Modification by {name}...Pausing timer {timer_name}"
                return_error(error=err_str, message=err_str)
            if re.search("paused", old):
                demisto.executeCommand("pauseTimer", {"timerField": timer})
                err_str = f"Invalid Timer Modification by {name}...Pausing timer {timer_name}"
                return_error(error=err_str, message=err_str)
    except Exception as ex:
        return_error(f'Failed to execute PreventTimerChange. Error: {str(ex)}')


''' ENTRY POINT '''


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
