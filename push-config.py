#!/usr/bin/env python

from pyats.topology import loader
import time

config_commands = """\
no ip access-list standard SNMP-ONLY
ip access-list standard SNMP-ONLY
 permit 192.168.1.254
 permit 192.168.1.250
 deny   any
exit
"""

#print(config_commands)
testbed = loader.load("testbed.yaml")

start_time = time.time()

testbed.connect(learn_hostname = True, init_exec_commands = [], init_config_commands = [])

testbed.configure(config_commands, error_pattern = [])
testbed.execute('write memory')

#testbed.execute('send log "Logging to splunk configured"')
#testbed.execute('clear lldp table')

testbed.disconnect()

print("Runtime of the program is %s seconds." %(time.time()-start_time))

