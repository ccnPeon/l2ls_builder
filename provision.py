import getpass
import sys
sys.path.append("./include")
from api import API
from deployment_functions import *
    
def main():
    
    ##############################################################################
    ############################## Common Variables ##############################
    ##############################################################################
    env_info = get_environment_info()
    username = input('Please enter your username: ')
    password = getpass.getpass('Please enter your password: ')


    ##############################################################################
    ############################## Pre-Provisioning ##############################
    ##############################################################################

    for datacenter in env_info['datacenters']:

        print('Deploying datacenter: ' + datacenter)
        # Instantiate client connection
        cvp_server = env_info['datacenters'][datacenter]['cvp_info']['cvp_hostname']
        client = API(cvp_server, username, password)

        # Get topology file
        topology = get_topology(datacenter)

        # # # # Create containers in toplogy
        create_containers(topology,client)

        # # Move devices from undefined to their proper container
        undefined_devices = client.get_devices_undefined()

        # print('Deploying Devices...')
        deploy_devices(topology,client,undefined_devices)


    ##############################################################################
    ################################# Deployment #################################
    ##############################################################################

        # Gather device and vlan info
        spine_info = yaml.safe_load(open('./topologies/{0}/spine_info.yaml'.format(datacenter), 'r').read())
        leaf_info = yaml.safe_load(open('./topologies/{0}/leaf_info.yaml'.format(datacenter), 'r').read())
        other_device_info = yaml.safe_load(open('./topologies/{0}/other_device_info.yaml'.format(datacenter), 'r').read())
        vlan_info = yaml.safe_load(open('./topologies/{0}/vlans.yaml'.format(datacenter), 'r').read())
        datacenter_container_info = client.get_container_by_name(datacenter)

        # Build datacenter management configlet
        build_vars = {**{'env_info': env_info['datacenters'][datacenter]}, **vlan_info}
        mgmt_config = render_config_template(build_vars,get_jinja_template('datacenter_mgmt'))
        mgmt_configlet_info = client.create_configlet(configlet_name=datacenter+'_MGMT',config=mgmt_config)
        if 'CreateConfigletError' in mgmt_configlet_info and mgmt_configlet_info['CreateConfigletError'] == 'Configlet may already exist.':
            mgmt_configlet_info = client.get_configlet_by_name(datacenter+'_MGMT')
        else:
            pass

        # Apply device specific configurations
        target_devices = get_target_devices(topology)
        cvp_devices = client.get_devices_provisioned()
        for cvp_device in cvp_devices:
            for target_name,target_values in target_devices.items():

                # Define a global list of configlets to apply
                configlets_to_apply = [mgmt_configlet_info]

                # Generate Device Management and apply to devices
                if cvp_device['ipAddress'] == target_values['ip']:
                    print('Creating configurations for Device: {0}'.format(target_name))
                    
                    if 'spine' in target_name.lower():
                        build_vars = {**{'env_info': env_info['datacenters'][datacenter]}, **{'device_type_info': spine_info}, **{'device_info': {**{'name': target_name}, **{'cvp_info': cvp_device}}}, **vlan_info, 'device_name': target_name, 'device_ip': target_values['ip']}
                    elif 'leaf' in target_name.lower():
                        build_vars = {**{'env_info': env_info['datacenters'][datacenter]}, **{'device_type_info': leaf_info}, **{'device_info': {**{'name': target_name}, **{'cvp_info': cvp_device}}}, **vlan_info, 'device_name': target_name, 'device_ip': target_values['ip']}
                    else:
                        build_vars = {**{'env_info': env_info['datacenters'][datacenter]}, **{'device_type_info': other_device_info}, **{'device_info': {**{'name': target_name}, **{'cvp_info': cvp_device}}}, **vlan_info, 'device_name': target_name, 'device_ip': target_values['ip']}
                    device_mgmt_config = render_config_template(build_vars,get_jinja_template('device_mgmt'))
                    configlet_info = client.create_configlet(target_name+'_MGMT',device_mgmt_config)
                    if 'CreateConfigletError' in configlet_info and configlet_info['CreateConfigletError'] == 'Configlet may already exist.':
                        configlet_info = client.get_configlet_by_name(target_name+'_MGMT')
                    else:
                        pass
                    configlets_to_apply.append(configlet_info)
                
                    # Generate Device Configurations for Spines
                    if 'spine' in target_name.lower():

                        # Generate Infrastructure config
                        template = get_jinja_template('spine_infra')
                        build_vars = {**{'env_info': env_info}, **{'device_type_info': spine_info}, **{'device_info': {**{'name': target_name}, **{'cvp_info': cvp_device}}}}
                        infra_config = render_config_template(build_vars,template)
                        configlet_info = client.create_configlet(target_name+'_INFRA',infra_config)
                        if 'CreateConfigletError' in configlet_info and configlet_info['CreateConfigletError'] == 'Configlet may already exist.':
                            configlet_info = client.get_configlet_by_name(target_name+'_INFRA')
                        else:
                            pass
                        
                        configlets_to_apply.append(configlet_info)

                        # Generate general configs
                        template = get_jinja_template('spine_config')
                        build_vars = {**{'env_info': env_info}, **{'device_type_info': spine_info}, **{'device_info': {'name': target_name}}, **{'vlan_info': vlan_info }}
                        config = render_config_template(build_vars,template)
                        configlet_info = client.create_configlet(target_name+'_CONFIG',config)
                        if 'CreateConfigletError' in configlet_info and configlet_info['CreateConfigletError'] == 'Configlet may already exist.':
                            configlet_info = client.get_configlet_by_name(target_name+'_CONFIG')
                        else:
                            pass
                        
                        configlets_to_apply.append(configlet_info)
                    
                    # Generate Device Configurations for Leafs
                    elif 'leaf' in target_name.lower():
                        template = get_jinja_template('leaf_infra')
                        build_vars = {**{'env_info': env_info}, **{'device_type_info': leaf_info}, **{'device_info': {**{'name': target_name, 'group': target_values['group']}, **{'cvp_info': cvp_device}}}}
                        infra_config = render_config_template(build_vars,template)
                        configlet_info = client.create_configlet(target_name+'_INFRA',infra_config)
                        if 'CreateConfigletError' in configlet_info and configlet_info['CreateConfigletError'] == 'Configlet may already exist.':
                            configlet_info = client.get_configlet_by_name(target_name+'_INFRA')
                        else:
                            pass
                        
                        configlets_to_apply.append(configlet_info)

                        # Generate general configs
                        config = ''
                        configlet_info = client.create_configlet(target_name+'_CONFIG',config)
                        if 'CreateConfigletError' in configlet_info and configlet_info['CreateConfigletError'] == 'Configlet may already exist.':
                            configlet_info = client.get_configlet_by_name(target_name+'_CONFIG')
                        else:
                            pass
                        
                        configlets_to_apply.append(configlet_info)

                        
                    client.add_multiple_configlets_to_device(configlets_to_apply,cvp_device)
                    
        # Apply DC Management to Containers
        client.add_configlet_to_container(mgmt_configlet_info['key'],mgmt_configlet_info['name'],datacenter_container_info)

    # Save Topology
    client.save_topology()

if __name__ == '__main__':
    main()