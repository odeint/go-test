#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import re
import subprocess
import yaml
import argparse
import pexpect
from pexpect import popen_spawn
import sys


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


PASS_STATUS = "%s[PASS]%s" % (bcolors.OKGREEN, bcolors.ENDC)
FAIL_STATUS = "%s[FAIL]%s" % (bcolors.FAIL, bcolors.ENDC)


MULTI_RUN_GROUPS = ("ladder")
DEFAULT_MULTI_RUNS = 1


group_score = {}
group_total = {}


def my_print(message):
    print(message, end="")


def print_status(moves, is_pass):
    message = ' '.join(moves) if isinstance(moves, list) else str(moves)
    print("%s %s" % (PASS_STATUS if is_pass else FAIL_STATUS, message))


def print_multi_status(results):
    pass_num = sum(x for x in results)
    color = bcolors.WARNING
    if pass_num == len(results):
        color = bcolors.OKGREEN
    elif pass_num == 0:
        color = bcolors.FAIL
    print("%s[%s/%s PASSES]%s" % (color, pass_num, len(results), bcolors.ENDC))


def debug(message):
    if args.debug:
        print("DEBUG: %s" % message, end='')


def find(values, value):
    try:
        return values.index(value)
    except ValueError:
        return -1


def update_score(test, result):
    group = test['group']
    group_total[group] = group_total.get(group, 0) + 1
    group_score[group] = group_score.get(group, 0) + (1 if result else 0)


def mock_single_test(test):
    result = False
    update_score(test, result)
    return ("TEST", result)

def do_single_test(test):
    cmd = command.replace("\\", "/")
    child = pexpect.popen_spawn.PopenSpawn(cmd, timeout=30, maxread=2000, searchwindowsize=None, 
                                       logfile=None, cwd=None, env=None, encoding=None, codec_errors='strict')
    
    child.expect('Leela:')
    lol1 = child.before
    lol1s = lol1.decode("unicode_escape")
    if test.get('number'):
        child.sendline('loadsgf ./sgf/%s %s' % (test['sgf'], test['number']))
    else:
        child.sendline('loadsgf ./sgf/%s' % test['sgf'])
    
    line = "loadsgf ./sgf/%s" % test['sgf']
    child.expect('Leela:')
    lol2 = child.before
    lol2s = lol2.decode("unicode_escape")
    child.sendline('genmove %s' % test['move'])
    child.expect('Leela:')
    lol3 = child.before
    lol3s = lol3.decode("unicode_escape")
    print(lol3s)
    child.sendline('quit')
      
    lines = []
    for outline in lol3s.splitlines():
        src = re.search("->",outline)
        if src:
            print(src.string)
            lines.append(src.string)

    print("LINES:\n"+str(lines))
    print("LINE :\n"+ line)
    print("LINES0 :\n"+lines[0])
    debug("%s\n" % line)
    
    bestline = lines[0]
    match = re.search('\(V: (\d+\.\d+)%\).+PV: (.+)', bestline)
    win_rate = float(match.group(1))
    moves = match.group(2).split(' ')
    next_move = moves[0]

    if test.get('yes_move'):
        yes_moves = [m.upper() for m in test['yes_move']]
        result = next_move in yes_moves
    elif test.get('no_move'):
        no_moves = [m.upper() for m in test['no_move']]
        result = next_move not in no_moves
    elif test.get('max_win_rate'):
        result = win_rate <= float(test['max_win_rate'])
    else:
        raise Exception("Neither yes_move, no_move or win_rate found")

    update_score(test, result)
    return (line, result)


parser = argparse.ArgumentParser(description='Scenario testing tool for Go')
parser.add_argument('--debug', action='store_true', help='Debug messages')
parser.add_argument('--command', help='Override the test command in config.yml')
parser.add_argument('--case', action='append',
                    help='Only run specify cases')

args = parser.parse_args()

with open("config.yml", 'r') as stream:
    config = yaml.load(stream)

if args.command:
    command = args.command
else:
    command = config['command']
tests = config['tests']

my_print("Command: %s\n" % command)

for test in tests:
    if args.case and test['sgf'] not in args.case:
        continue
    my_print("%s\n" % test['sgf'])
    if test['group'] in MULTI_RUN_GROUPS:
        results = []
        for i in range(0, DEFAULT_MULTI_RUNS):
            my_print("%s " % i)
            (line, result) = do_single_test(test)
            results.append(result)
        my_print("\n")
        print_multi_status(results)
    else:
        (line, result) = do_single_test(test)
        print_status(line, result)

for group in group_score:
    color = bcolors.WARNING
    if group_score[group] == 0:
        color = bcolors.FAIL
    elif group_score[group] == group_total[group]:
        color = bcolors.OKGREEN
    my_print("%s: %s[%s/%s PASSES]%s\n" % (group, color, group_score[group], group_total[group], bcolors.ENDC))
#%%
