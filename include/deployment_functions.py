import yaml
import json
import jinja2
import requests
requests.packages.urllib3.disable_warnings() 
import datetime
import os

def get_environment_info():
    with open('./global_variables/environment_variables.yaml', 'r') as env_file:
        env_info = yaml.safe_load(env_file.read())
        return env_info

def get_topology(datacenter):
    with open('./topologies/{0}/topology_info.yaml'.format(datacenter), 'r') as topology_file:
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

def deploy_devices(topology,client,undefined_devices):
    
    for container in topology:
        for device in undefined_devices:
            if topology[container] and 'devices' in topology[container]:
                for search_device in topology[container]['devices']:
                    if device['ipAddress'] == topology[container]['devices'][search_device]['ip']:
                        print('Staging {0} to be moved to {1}'.format(device['fqdn'],container))
                        device_list = [{device['fqdn']: container}]
                        client.move_devices(device_list)
                    else:
                        pass
            
        if topology[container] != None and 'children' in topology[container]:
            deploy_devices(topology[container]['children'],client,undefined_devices)

def get_target_devices(topology):
    
    target_devices = {}
    
    for container in topology:
        if topology[container] and 'devices' in topology[container]:
            for device in topology[container]['devices']:
                target_devices[device] = {'ip': topology[container]['devices'][device]['ip'], 'group': container }
        
        if topology[container] != None and 'children' in topology[container]:
            target_devices.update(get_target_devices(topology[container]['children']))

    return target_devices

def get_jinja_template(configlet_type):
    if configlet_type == 'datacenter_mgmt':
        template_path = 'datacenter_mgmt_template.j2'
    elif configlet_type == 'device_mgmt':
        template_path = 'device_mgmt_template.j2'
    elif configlet_type == 'spine_infra':
        template_path = 'spine_infra_template.j2'
    elif configlet_type == 'spine_config':
        template_path = 'spine_config_template.j2'
    elif configlet_type == 'leaf_infra':
        template_path = 'leaf_infra_template.j2'

    with open('./jinja/{0}'.format(template_path), 'r') as j2:
        template = j2.read()
        j2.close()
        return template

def render_config_template(vars_dict,template):
    env = jinja2.Environment(
        loader=jinja2.BaseLoader(),
        trim_blocks=True,
        extensions=['jinja2.ext.do'])
    templategen = env.from_string(template)
    if templategen:
        config = templategen.render(vars_dict)
        return(config)
    return(None)