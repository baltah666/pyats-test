#!/usr/bin/env python

from encodings import utf_8
import json
import requests
import yaml
import jinja2
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    'X-Auth-Token': '4f448a042f7cbfcc875c3be51627f100',
}

response = requests.get('http://192.168.1.254:8081/api/v0/devices', headers=headers, verify=False)

api_data = json.loads(response.content)

keys = ['dev_name', 'dev_alias', 'dev_os', 'dev_ip', 'dev_net_type', 'dev_netmiko_type']
values = []
inventory_dict = {'inventory': []}
count = 0
print("Location,Alias,IP,PID,Version")

for i in api_data['devices']:
    if (i['os'] == 'ios' or i['os'] == 'iosxe')  and (i['status'] != 0) and ('C9200CX-8P-2X2G' in i['hardware']):
        dev_name = i['hostname']
        dev_alias = i['hostname'].split('.')[0]
        dev_os = i['os']
        dev_ip = i['ip']
        dev_net_type = 'accessctrl-techit'
        dev_netmiko_type = 'cisco_ios'
        dev_hardware = i['hardware']
        dev_version = i['version']
        count = count + 1
        inventory_dict['inventory'].append(dict(zip(keys, values)))
        print(f"{dev_alias},{dev_ip},{dev_hardware},{dev_version}")

#print(inventory_dict)
print(count)

with open("./pyats_inventory_access.json", "w+", encoding="utf_8") as inventory_file:
    inventory_file.write(json.dumps(inventory_dict, indent=4))

# env = jinja2.Environment(loader=FileSystemLoader('.'), trim_blocks=True, lstrip_blocks=True)
env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))
template = env.get_template('pyats_testbed_template.j2')
rendered_template = template.render(**inventory_dict)
# print(rendered_template)

with open("./C9200CX-8P-2X2Gtestbedaccess.yaml", "w+", encoding="utf_8") as pyats_testbed_file:
    pyats_testbed_file.write(rendered_template)


