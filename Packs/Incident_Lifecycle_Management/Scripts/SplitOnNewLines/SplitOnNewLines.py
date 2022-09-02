import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
from CommonServerPython import __line__

register_module_line('SplitOnNewLines', 'start', __line__())


def split_lines(args):
    the_str = args.get('value')
    res = str(the_str).splitlines()
    if res is None:
        res = []
    return res


def main():
    try:
        args: dict = demisto.args()
        return_results(split_lines(args))

    except Exception:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute SplitOnNewLines. Error: {traceback.format_exc()}')


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
register_module_line('SplitOnNewLines', 'end', __line__())
