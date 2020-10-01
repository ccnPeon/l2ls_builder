import getpass
import sys
sys.path.append("./include")
from api import API
from deployment_functions import *

    
def main():

    env_info = get_environment_info()
    username = input('Please enter your username: ')
    password = getpass.getpass('Please enter your password: ')
    cvp_server = env_info['datacenters']['DCA']['cvp_info']['cvp_hostname']
    # Instantiate client connection
    client = API(cvp_server, username, password)

    devices = client.get_devices_provisioned()

    for device in devices:
        print('Removing device: {0}'.format(device['fqdn']))
        client.delete_device_by_id(device['systemMacAddress'])

if __name__ == '__main__':
    main()