#!/usr/bin/python

## ################################################################################
## the package and lib that must install:
##
## OpenIPMI
##  yum install OpenIPMI-python
##
## Pexpect:Version 3.3 or higher
##  caution: a lower version will cause some error like "timeout nonblocking() in read" when you log to a host by ssh
##      wget https://pypi.python.org/packages/source/p/pexpect/pexpect-3.3.tar.gz
##      tar xvf pexpect-3.3.tar.gz
##      cd pexpect-3.3
##      python setup install
##
##
## Be aware:
##    2014-08-24 : using multiprocessing.dummy to archieve multi-thread instead of multi-processing with multiprocessing
##         in multi-process, the function pssh will cause error like "local variable 's' referenced before assignment"
##  
## ################################################################################


import sys
import pxssh
import pexpect
import os
import time
from multiprocessing import Pool
import subprocess
import OpenIPMI

def pssh((hostname, username, password, cli)):
    try:
        s = pxssh.pxssh()
        s.login(hostname, username, password)
	s.sendline(cli)
        s.prompt()
    except (pexpect.EOF, Exception), e:
        print hostname, s.before
        return [hostname, s.before]
    finally:
        s.close()

def chk(hostname):
    pin = subprocess.call(("ping -c 1 -t 1 %s" % (hostname)).split(" "))
    return [hostname, pin]

def chk_pxe(hostname):
    chkstatus=subprocess.Popen(("ipmitool -l lanplus -H %s -U admin -P admin chassis power status" % (hostname)).split(" "),stdout=subprocess.PIPE)
    rs,re=chkstatus.communicate()
    return [hostname, rs]

def pxe(hostname):
    print "pxe %s" % hostname
    pxeboot = subprocess.call(("ipmitool -l lanplus -H %s -U admin -P admin chassis bootdev pxe" % (hostname)).split(" "))
    reset = subprocess.call(("ipmitool -I lanplus -H %s -U admin -P admin power reset" % (hostname)).split(" "))
    print hostname, "is rebooting"
    return [hostname, reset]

if __name__ == '__main__':
    hosts = []
    pingfail = []
    ethsuccess = []
    etherror = []
    rebootfail = []
    failafterreboot = [] 
    successnode = [] 
    starttime = time.time()
    pool = Pool(processes = 10)
    username = "root"
    password = "root"
    ipminet="10.0.0"
    net = "10.1.0"
    ipsegs = []
    rebootHostCount=2 ## per 5 seconds
   
    ipsegs.append((80,84))  # [80,84] including 84
    
    with open('pingerror.log','w') as file :
        file.truncate() 
    with open('eth6Fail.log','w') as file :
	file.truncate()
    with open('reboot.log','w') as file :
	file.truncate()

    # check ping
    for ipseg in ipsegs :
    	res = pool.map_async(chk, ((net+'.'+str(ip)) for ip in range(ipseg[0], ipseg[1]+1))) 
    	result = res.get()
    	for host in result:
            if host[1] == 0:
            	hosts.append(host[0])
            else:
            	pingfail.append(host[0])

    print pingfail
    
    if pingfail:
    	with open('pingerror.log','w') as file:
	    for node in pingfail:
	    	file.write(node+'\n')

    # check eth6 in pingsuccess hosts
    if hosts:
        cli = "ifconfig eth6;"
        cli += 'exit $?'
        print cli
        from multiprocessing.dummy import Pool
        poolDummy = Pool(processes = 10)
        res = poolDummy.map_async(pssh, (((net+'.'+str(ip)[len(net)+1:]), username, password, cli) for ip in hosts))
        result = res.get()
        poolDummy.close()
	poolDummy.join()
        for host in result:
            print 'return',host[1],'xx'
            if ("Device not found" in host[1]) or (host[1] == ''):
                ethsuccess.append(host[0])
            else:
                etherror.append(host[0])

        if etherror:
            print "eth6 existed %s nodes as listed:" % len(etherror)

	    with open('eth6Fail.log','w') as file:
            	for node in etherror:
                    print node
		    file.write(node+'\n')
    pool.close()
    pool.join()

    # reboot to continue check 
    reboot = ethsuccess ## extend the list to choose the reboot hosts
    rebootInterval = 5 #second
    checkrebootstatus = 600 / rebootInterval
    inreboot = {}
   
    if reboot:
        while 1:
            # reboot the remain host
            for cnt in range(1,rebootHostCount) :
                if reboot :
                    host = pxe((ipminet+'.'+str(reboot[0])[len(net)+1:]))
                    if host[1] == 1:
 			rebootfail.append(host[0])
                        print host[0], ":fail to set pxe"
			with open('rebootfail.log','a') as file:
			    file.write(host[0])
                    else:
                        print host[0], ":success to set pxe"
                        inreboot[host[0]] = checkrebootstatus
                    del reboot[0]
		else:
		    break

            # check the status of host reached the check time
	    waitdel=[]
            for host in inreboot :
                if inreboot[host] == 0:
                    res = chk(net+'.'+str(host)[len(net)+1:])
                    if res[1] == 0:
                        successnode.append(host)
			print res[0],"********* success after reboot"
                    else:
                        failafterreboot.append(res[0])
			print "!!!!!!!!! cannot enter the OS after reboot :%s" % host
		    waitdel.append(host)
		else:
		    inreboot[host] = inreboot[host] - 1

	    for host in waitdel:
		del inreboot[host] 
	    waitdel = []

            if reboot or inreboot :
                print 'in rebooting and checking,please wait......'
                time.sleep(rebootInterval)
            else:
                break;

        with open('reboot.log','w') as file : 
            for node in rebootfail : 
	        file.write('fail reboot:'+node+'\n')
	    for node in failafterreboot :
		file.write('fail after reboot :'+node+'\n')
	    for node in successnode :
		file.write('success:'+node+'\n')

    print 'all result display :'
    if pingfail :
	print 'ping fail node:'
	for node in pingfail :
		print node
    if etherror :
	print 'eth6 error:'
	for node in etherror :
	    print node
    if successnode :
	print 'success node :'
	for node in successnode :
	    print node
    if failafterreboot :
	print 'fail after reboot node :'
	for node in failafterreboot :
	    print node
    if  rebootfail :
	print 'fail 2 reboot :'
	for node in rebootfail :
	    print node
