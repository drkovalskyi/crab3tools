#!/bin/env python
import commands,re,subprocess
from CRABAPI.RawCommand import crabCommand

def get_tasks():
    report = commands.getoutput("find ./ -maxdepth 1 -type d -name 'crab_*'")
    lines = report.split("\n")
    tasks = []
    for line in lines:
        if re.search('crab_configs',line): continue
        tasks.append(line)
    return tasks

tasks = get_tasks()
for task in tasks:
    print "\n",task
    report = crabCommand('status', dir = task)
    if 'jobsPerStatus' in report:
        if 'failed' in report['jobsPerStatus']:
            print "Found failed jobs. Resubmit"
            crabCommand('resubmit', dir = task)
    # process = subprocess.Popen("crab resubmit -d %s"%task, shell=True)
    # process.wait()
    # print process.returncode
                
