import yaml
import json
import getpass
import sys
sys.path.append("../include/api")
from api import API
import requests
requests.packages.urllib3.disable_warnings() 
import datetime
import os

def get_environment_info():
    with open('../variables/environment_variables.yaml', 'r') as env_file:
        env_info = yaml.safe_load(env_file.read())
        return env_info

def get_topology():
    with open('../variables/topology_info.yaml', 'r') as topology_file:
        topology = yaml.safe_load(topology_file.read())
        return topology

def create_containers(container_info,client,parent=''):
    # Create new configlets if they don't already exist
    for key,values in container_info.items():
        current_container_name = key
        container_info = values
        
        # Iterate thorugh containers and pull out name into list
        current_containers = [container['Name'] for container in client.get_containers()]
        if current_container_name not in current_containers:
            print('Creating container {0}'.format(current_container_name))
            client.create_container(current_container_name,parent)
        else:
            pass
        
        # Recurse this function and send children if it exists
        if values and 'children' in values:
            create_containers(values['children'],client,parent=current_container_name)


def deploy_devices(topology,client,undefined_devices,username,password):
    
    for container in topology:
        for device in undefined_devices:
            if topology[container] != None and 'devices' in topology[container] and topology[container]:
                if device['ipAddress'] in topology[container]['devices']:
                    print('Staging {0} to be moved to {1}'.format(device['fqdn'],container))
                    device_list = [{device['fqdn']: container}]
                    client.move_devices(device_list)
                    if device['ztpMode'] == True:
                        create_configlet_from_configuration_file(client,device)
                    else:
                        create_configlet_from_running_config(client,device,username,password)
            
        if topology[container] != None and 'children' in topology[container]:
            deploy_devices(topology[container]['children'],client,undefined_devices,username,password)

    


def create_configlet_from_running_config(client,device,username,password):
    payload = {'data': []}
    # Get running configuration
    url = 'https://{0}/command-api'.format(device['ipAddress'])
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {
            "format": "text",
            "timestamps": False,
            "autoComplete": False,
            "expandAliases": False,
            "cmds": [
            "enable",
            "show running-config | exclude !|^end$"
            ],
            "version": 1
        },
        "id": "EapiExplorer-1"
        })
    configuration = json.loads(requests.post(url=url, data=payload, auth=(username,password), verify=False).content)['result'][1]['output']
    
    # Create Configlet in CVP
    configlet_info = client.create_configlet(configlet_name=device['fqdn']+'_MGMT',config=configuration)

    # Add configlet to device
    return client.add_configlet_to_device(configlet_info['key'], configlet_info['name'], device)

def create_configlet_from_configuration_file(client,device):
    payload = {'data': []}
    configuration = ''
    # Get configuration from file
    for config_file in os.listdir('./config_files'):
        if config_file[:-5] == device['ipAddress']:
            with open('./config_files/'+config_file, 'r') as config_data:
                configuration = config_data.read()
    
    # Get hostname for configlet name
    hostname = ''
    for line in configuration.splitlines():
        if 'hostname' in line:
            hostname = line[9:]
    
    # Create Configlet in CVP
    configlet_info = client.create_configlet(configlet_name=hostname+'_MGMT',config=configuration)

    # Add configlet to device
    return client.add_configlet_to_device(configlet_info['key'], configlet_info['name'], device)
    

def main():
    
    env_info = get_environment_info()
    username = input('Please enter your username: ')
    password = getpass.getpass('Please enter your password: ')
    cvp_server = env_info['cvp_server']

    # Instantiate client connection
    client = API(cvp_server, username, password)

    # Get topology file
    topology = get_topology()

    # Create containers in toplogy
    create_containers(topology,client)

    # Move devices from undefined to their proper container
    undefined_devices = client.get_devices_undefined()

    print('Deploying Devices...')
    deploy_devices(topology,client,undefined_devices,username,password)

    # Save Changes and execute tasks
    task_list = client.save_topology()['data']['taskIds']
    client.execute_tasks(task_list)


if __name__ == '__main__':
    main()