import json
import requests
requests.packages.urllib3.disable_warnings() 
import datetime

class API():
    def __init__(self,server,username,password):
        self.api_root = 'https://{0}/cvpservice'.format(server)
        self.cookies = self._auth(username,password)

    def _auth(self,username,password):
        payload = json.dumps({'userId': username, 'password': password})
        url = self.api_root + '/login/authenticate.do'
        response = requests.post(url=url, data=payload, verify=False)
        if 'Invalid credentials' in response.text:
            print("Invalid credentials.")
            quit()
        else:
            return response.cookies

    # Container Operations
    def get_containers(self):
        url = self.api_root + '/inventory/containers'
        response = json.loads(requests.get(url=url, verify=False, cookies=self.cookies).content)
        return response

    def get_container_by_name(self,container_name):
        url = self.api_root + '/inventory/containers?name={0}'.format(container_name)
        response = json.loads(requests.get(url=url, verify=False, cookies=self.cookies).content)[0]
        return response
    
    def get_container_by_key(self,container_key):
        url = self.api_root + '/inventory/containers?key={0}'.format(container_key)
        response = json.loads(requests.get(url=url, verify=False, cookies=self.cookies).content)[0]
        return response

    def create_container(self,container_name,container_parent=''):
        url = self.api_root + '/provisioning/addTempAction.do?format=topology&queryParam=&nodeId=root'

        payload = {'data': []}
        temp_data = {'info': 'Add Container',
                        'infoPreview': 'Add Container',
                        'action': 'add',
                        'nodeType': 'container',
                        'nodeId': 'new_container',
                        'toId': '',
                        'fromId': '',
                        'nodeName': container_name,
                        'fromName': '',
                        'toName': '',
                        'childTasks': [],
                        'parentTask': '',
                        'toIdType': 'container'}
        
        if container_parent != '':
                temp_data['toId'] = self.get_container_by_name(container_parent)['Key']
                temp_data['toName'] = container_parent
        
        # Add temp data to payload
        payload['data'].append(temp_data)
        response = json.loads(requests.post(url=url, data=json.dumps(payload), cookies=self.cookies, verify=False).content)

        # Save topology so that children can be created if needed
        self.save_topology()
        
        return response
    
    def save_topology(self):
        url = self.api_root + '/provisioning/v2/saveTopology.do'
        response = json.loads(requests.post(url=url, data='[]', cookies=self.cookies, verify=False).content)
        return response

    # Device Operations
    def get_devices_undefined(self):
        url = self.api_root + '/provisioning/getNetElementList.do?nodeId=undefined_container&startIndex=0&endIndex=0&ignoreAdd=true'
        response = json.loads(requests.get(url=url, cookies=self.cookies, verify=False).content)['netElementList']
        return response

    def get_devices_all(self):
        url = self.api_root + '/inventory/devices?provisioned=true'
        response = json.loads(requests.get(url=url, cookies=self.cookies, verify=False).content)
        return response
    
    def get_device_by_name(self,device_name):
        url = self.api_root + '/provisioning/searchTopology.do?queryParam={0}&startIndex=0&endIndex=0'.format(device_name)
        response = json.loads(requests.get(url=url, cookies=self.cookies, verify=False).content)['netElementList'][0]
        if response['fqdn'] == device_name:
            return response
        else:
            return {'Error': 'Device name mismatch. Multiple devices may have been found.'}

    def move_devices(self,device_list):
        '''
        Moves List of Devices from one container to another

        Args:
            device_list: list(dict{device_name: target_container})
        '''
        current_containers = self.get_containers()
        payload = {'data': []}
        for item in device_list:
            device_name, target_container = next(iter(item.items()))
            device_info = self.get_device_by_name(device_name)
            target_container_id = self.get_container_by_name(target_container)['Key']
            temp_data = {'info': 'Move Device {0}'.format(device_name),
                'infoPreview': 'Move Device {0}'.format(device_name),
                'action': 'update',
                'nodeType': 'netelement',
                'nodeId': device_info['key'],
                'toId': target_container_id,
                'fromId': device_info['parentContainerId'],
                'nodeName': device_name,
                'toName': target_container,
                'toIdType': 'container',
                'childTasks': [],
                'parentTask': ''}

            payload['data'].append(temp_data)

        url = self.api_root + '/provisioning/addTempAction.do?format=topology&queryParam=&nodeId=root'
        response = json.loads(requests.post(url=url, data=json.dumps(payload), cookies=self.cookies, verify=False).content)
        if 'errorMessage' in response:
            return {'MoveDeviceError': response['errorMessage']}
        else:
            return {'MoveDevice': 'Device Moves Successfully Staged'}
    
    # Task Operations
    def get_tasks(self,query_param=''):
        url = self.api_root + '/task/getTasks.do?'
        if query_param:
            url += 'queryparam=' + query_param
            url += '&startIndex=0&endIndex=50'
        else:
           url += 'startIndex=0&endIndex=50'
        response = json.loads(requests.get(url=url, cookies=self.cookies, verify=False).content)['data']
        return(response)

    def get_task_by_id(self,task_id):
        url = self.api_root + '/task/getTaskById.do?taskId={0}'.format(task_id)
        response = json.loads(requests.get(url=url, cookies=self.cookies, verify=False).content)
        return response

    def execute_tasks(self,task_list):
        payload = json.dumps({'data': task_list})
        url = self.api_root + '/task/executeTask.do'
        response = requests.post(url=url, data=payload, cookies=self.cookies, verify=False).content
        return response
    
    # Configlet Operations
    def get_configlets(self):
        url = self.api_root + '/configlet/getConfiglets.do?startIndex=0&endIndex=0'
        response = json.loads(requests.get(url=url, cookies=self.cookies, verify=False).content)['data']
        return response
    
    def get_configlet_by_name(self,configlet_name):
        url = self.api_root + '/configlet/getConfigletByName.do?name={0}'.format(configlet_name)
        response = json.loads(requests.get(url=url, cookies=self.cookies, verify=False).content)
        return response

    def create_configlet(self,configlet_name,config):
        payload = json.dumps({'config': config, 'name': configlet_name})
        url = self.api_root + '/configlet/addConfiglet.do'
        response = json.loads(requests.post(url=url, data=payload, cookies=self.cookies, verify=False).content)

        if 'data' not in response:
            return {'CreateConfigletError': 'Configlet may already exist.'}
        else:
            return response['data']

    def get_configlets_by_device_id(self,device_id):
        url = self.api_root + '/provisioning/getConfigletsByNetElementId.do?netElementId={0}&startIndex=0&endIndex=0'.format(device_id.replace(':', '%3A'))
        response = json.loads(requests.get(url=url, cookies=self.cookies, verify=False).content)['configletList']
        return response

    def add_configlet_to_device(self,configlet_key,configlet_name,device_info,parent_task=''):
        payload = json.dumps({'data': [{'info': 'Add Configlet',
            'infoPreview': 'Add Configlet',
            'note': '',
            'action': 'associate',
            'nodeType': 'configlet',
            'nodeId': '',
            'configletList': [configlet_key],
            'configletNamesList': [configlet_name],
            'ignoreConfigletNamesList': [],
            'ignoreConfigletList': [],
            'configletBuilderList': [],
            'configletBuilderNamesList': [],
            'ignoreConfigletBuilderList': [],
            'ignoreConfigletBuilderNamesList': [],
            'toId': device_info['systemMacAddress'],
            'toIdType': 'netelement',
            'fromId': '',
            'nodeName': '',
            'fromName': '',
            'toName': device_info['fqdn'],
            'nodeIpAddress': device_info['ipAddress'],
            'nodeTargetIpAddress': device_info['ipAddress'],
            'childTasks': [],
            'parentTask': parent_task}]})
        
        url = self.api_root + '/provisioning/addTempAction.do?format=topology&queryParam=&nodeId=root'
        response = requests.post(url=url, data=payload, cookies=self.cookies, verify=False).content
        return response

    def update_device_configlets(self,configlets_to_add_keys,configlet_to_add_names,device_info,configlets_to_ignore_names,configlets_to_ignore_keys,parent_task=''):
        payload = json.dumps({'data': [{'info': 'Update Configlets',
            'infoPreview': 'Update Configlets',
            'note': '',
            'action': 'associate',
            'nodeType': 'configlet',
            'nodeId': '',
            'configletList': configlets_to_add_keys,
            'configletNamesList': configlet_to_add_names,
            'ignoreConfigletNamesList': configlets_to_ignore_names,
            'ignoreConfigletList': configlets_to_ignore_keys,
            'configletBuilderList': [],
            'configletBuilderNamesList': [],
            'ignoreConfigletBuilderList': [],
            'ignoreConfigletBuilderNamesList': [],
            'toId': device_info['systemMacAddress'],
            'toIdType': 'netelement',
            'fromId': '',
            'nodeName': '',
            'fromName': '',
            'toName': device_info['fqdn'],
            'nodeIpAddress': device_info['ipAddress'],
            'nodeTargetIpAddress': device_info['ipAddress'],
            'childTasks': [],
            'parentTask': parent_task}]})
        
        url = self.api_root + '/provisioning/addTempAction.do?format=topology&queryParam=&nodeId=root'
        response = requests.post(url=url, data=payload, cookies=self.cookies, verify=False).content
        return response

    def update_configlet(self,configlet_key,configlet_name,config,reconciled=False,wait_for_tasks=False):
        payload = json.dumps({
            "config": config,
            "key": configlet_key,
            "name": configlet_name,
            "waitForTaskIds": wait_for_tasks,
            "reconciled": reconciled
            })
        url = self.api_root + '/configlet/updateConfiglet.do'
        response = requests.post(url=url, data=payload, cookies=self.cookies,verify=False).content
        return response