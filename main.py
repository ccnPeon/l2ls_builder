#TODO make MLAG autobuild, management build, and potentially turn this into a leaf builder too.
import requests
from getpass import getpass
import urllib3
import json
import yaml
import jinja2
import sys
sys.path.append('./include/api')
from api import API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_environment_info():
    with open('./variables/environment_variables.yaml', 'r') as env_file:
        env_info = yaml.safe_load(env_file.read())
        return env_info

def get_topology():
    with open('./variables/topology_info.yaml', 'r') as topology_file:
        topology = yaml.safe_load(topology_file.read())
        return topology

def get_jinja_template(configlet_type):
    if configlet_type == 'mgmt':
        template_path = 'mgmt_template.j2'
    elif configlet_type == 'spine':
        template_path = 'spine_template.j2'
    elif configlet_type == 'leaf':
        template_path = 'leaf_template.j2'

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

def main():
    env_info = get_environment_info()
    # username = input('Please enter your username: ')
    # password = getpass('Please enter your password: ')
    cvp_server = env_info['cvp_server']
    topology = get_topology()
    spine_info = yaml.safe_load(open('./variables/spine_info.yaml', 'r').read())
    leaf_info = yaml.safe_load(open('./variables/leaf_info.yaml', 'r').read())
    vlan_info = yaml.safe_load(open('./variables/vlans.yaml', 'r').read())

    # Instantiate client connection
    client = API(cvp_server, username, password)

    # Get devices from CVP
    cvp_devices = client.get_devices_all()

    #temp offline data
    # cvp_devices = yaml.safe_load(open('offline_data.yaml', 'r').read())

    # Start to build one dict for build
    build_vars = {**{'env_info': env_info}, **vlan_info}

    mgmt_config = render_config_template(build_vars,get_jinja_template('mgmt'))

    for device in cvp_devices:
        if 'leaf' in device['fqdn'].lower():
            template = get_jinja_template('leaf')

            # Append Parent Container name to the device_info variable to use
            # for the MLAG Domain ID. Use camelCase to keep data consistent with 
            # CVP's API naming conventions.
            # device_info['parentContainer'] = client.get_container_by_key(device_info['parentContainerKey'])
            
            build_vars = {**build_vars, **{'device_type_info': leaf_info}, **{'device_info': device, **{'vlan_info': vlan_info}}}
        
            config = render_config_template(build_vars,template)
            print(config)
            break
        # elif 'spine' in device['fqdn'].lower():
        #     template = get_jinja_template('spine')
        #     build_vars = {**build_vars, **{'device_type_info': spine_info}, **{'device_info': device}}
        #     config = render_config_template(build_vars,template)
        #     print(config)




if __name__ == '__main__':
    main()