#!/usr/bin/python

import sys
import os
from time import time
from multiprocessing import Pool
import subprocess
import OpenIPMI


def chk(hostname):
    chkstatus=subprocess.Popen(("ipmitool -l lanplus -H %s -U admin -P admin chassis power status" % (hostname)).split(" "),stdout=subprocess.PIPE)
    rs,re=chkstatus.communicate()
    return [hostname, rs]

if __name__ == '__main__':
    fails = []
    pool = Pool(processes = 10)
    net = "10.0.0"
    ipstart = 8
    ipend = 144
    res = pool.map_async(chk, ((net+'.'+str(ip)) for ip in range(ipstart, ipend)))
    result = res.get()

    with open('fail.txt', 'w') as fail_file: # truncate the existed file's context
	fail_file.truncate()

    with open('fail.txt', 'a') as fail_file: # save the fail hostnames to file
	for host in result:
	    # if the output contains the power status string "Chassis Power is",it implies the ipmi is in valid
	    if "Chassis Power is" not in host[1]:
	        fails.append(host[0])
		fail_file.write(host[0]+'\n')

    if fails:
	print "Those nodes fail to reach bmc:\n",fails

