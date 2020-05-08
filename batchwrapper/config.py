# Copyright (c) Microsoft Corporation
#
# All rights reserved.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#
# @author: asedighi

from azure.common.credentials import ServicePrincipalCredentials
import json 

import os
import time
import random

DEFAULT_LOCATION = 'eastus'



def getRandomizer():
###    timestamp = int(time.time()* random.random())
    timestamp = int(time.time()* 10000)
    return str(timestamp)



def find_file_path(name, path="../../.."):
    for root, dirs, files in os.walk(path):
        ####print("{} {} {}".format(root, dirs, files))
        if name in files:
            return os.path.join(root, name)

    return None


class ReadConfig():
    def __init__(self, name=''):
        config = name

        json_config = ''

        if os.path.isfile(config):
            print("Found {}".format(config))
            with open(config) as json_data:
                json_config = json.load(json_data)

        else:
            my_path = find_file_path(name, "../")
            print("found: {}".format(my_path))
            if os.path.isfile(my_path):
                with open(my_path) as json_data:
                    json_config = json.load(json_data)

        return  json_config




class AzureCredentials():
   
    def __init__(self):
        '''
        Constructor
        '''
        self.cred = ''

        if os.path.isfile('./credentials.json'):
            print("Found credentials.json in current directory")
            with open('./credentials.json') as json_data:
                self.cred = json.load(json_data)

        else:
            my_path = find_file_path("credentials.json", "../")
            if my_path == None:
                print("I was not able to find the credentials.json file... exiting....")
                exit(-1)
            print("found: {}".format(my_path))
            if os.path.isfile(my_path):
                with open(my_path) as json_data:
                    self.cred = json.load(json_data)

        '''
        application or client id are the same
        '''
        self.batch_account_name = self.cred['BATCH_ACCOUNT_NAME']
        self.batch_account_key = self.cred['BATCH_ACCOUNT_KEY']
        self.batch_account_url = self.cred['BATCH_ACCOUNT_URL']
        self.storage_connection_string = self.cred['STORAGE_CONNECTION_STRING']
        self.service_bus_connection_string = self.cred['SERVICEBUS_CONNECTION_STRING']


        self.LOCATION = DEFAULT_LOCATION

        
        
    def getLocation(self):
        return self.LOCATION
    
    def setLocation(self, location):
        self.LOCATION = location
    
    
    def getBatchAccountName(self):
        return self.batch_account_name
    
    def getBatchAccountKey(self):
        return self.batch_account_key
    
    def getBatchAccountUrl(self):
        return self.batch_account_url
    
    def getStorageConnectionString(self):
        return self.storage_connection_string


    def get_service_bus_connection_string(self):
        return self.service_bus_connection_string
'''
{
	"BATCH_NODE_COUNT": 2,
	"v": "BASIC_A1",
	"BATCH_OS_PUBLISHER":"Canonical",
	"BATCH_OS_TYPE": "UbuntuServer",
	"BATCH_OS_VERSION": 16
}
'''



class AzureBatchConfiguration():

    def __init__(self):

        self.batch = ''


        if os.path.isfile('./batch.json'):
            print("Found batch.json in current directory")
            with open('./batch.json') as json_data:
                self.batch = json.load(json_data)

        else:
            my_path = find_file_path("batch.json", "../")

            print("Found: {}".format(my_path))

            if os.path.isfile(my_path):
                with open(my_path) as json_data:
                    self.batch = json.load(json_data)

        self.batch_node_count = self.batch['BATCH_NODE_COUNT']
        self.batch_vm_size = self.batch['BATCH_VM_SIZE']
        self.batch_os_publisher = self.batch['BATCH_OS_PUBLISHER']
        self.batch_os_type = self.batch['BATCH_OS_TYPE']
        self.batch_os_version = self.batch['BATCH_OS_VERSION']
        self.batch_engine_name = self.batch['BATCH_ENGINE_NAME']


    def getNodeCount(self):
        return self.batch_node_count

    def getVMSize(self):
        return self.batch_vm_size


    def getOSPublisher(self):
        return self.batch_os_publisher

    def getOSType(self):
        return self.batch_os_type

    def getOSVersion(self):
        return self.batch_os_version


    def getEngineName(self):
        return self.batch_engine_name



class TaskConfig():
    def __init__(self):

        self.task = ''
        if os.path.isfile('tasks/task.json'):
            print("Found task.json in current directory")
            with open('./task.json') as json_data:
                self.task = json.load(json_data)

        else:
            my_path = find_file_path("task.json", "../")

            print("found: {}".format(my_path))
            if os.path.isfile(my_path):
                with open(my_path) as json_data:
                    self.task = json.load(json_data)

        self.task_modules = self.task['TASK_MODULES']
        self.task_args = self.task['TASK_ARGS']
        self.task_output = self.task['TASK_OUTPUT_CONTAINER']

        self.task_modules_dir = self.task['TASK_MODULES_DIRECTORY']

    def getTaskModules(self):
        return self.task_modules

    def getTaskModulesDir(self):
        return self.task_modules_dir

    def getTaskArgs(self):
        return self.task_args

    def getOutputContainer(self):
        return self.task_output

class TaskManifest():

    ## return a list of tuples (task executable, task input)

    def __init__(self, manifest_file: str):

        self.manifest = ''
        if os.path.isfile(manifest_file):
            print("Found {} in current directory".format(manifest_file))
            with open(manifest_file) as json_data:
                self.manifest = json.load(json_data)

        else:
            my_path = find_file_path(manifest_file, "../")

            print("Found manifest in: {}".format(my_path))
            if os.path.isfile(my_path):
                with open(my_path) as json_data:
                    self.manifest = json.load(json_data)

        self.tasks = self.manifest['JOB_MANIFEST']


    def get_tasks(self) -> list:

        json_data = []  # your list with json objects (dicts)

        for item in json_data:
            for data_item in item['data']:
                print
                data_item['name'], data_item['value']

        task_list = list()


        all_tasks = self.tasks

        for item in all_tasks:
            task_list.append((item['TASK_MODULE'], item['TASK_INPUT']))


        print(task_list)

        return task_list
'''


        for i in range(len(all_tasks)):
            key = i['TASK_MODULE']
            val = i['TASK_INPUT']
            task_list.append((key,val))

        print(task_list)
        return task_list

'''

if __name__ == '__main__':


    print(getRandomizer())
    print(getRandomizer())
    print(getRandomizer())
    print(getRandomizer())
    print(getRandomizer())

    manifest = TaskManifest("task.json")
    tasks = manifest.get_tasks()


    # i have a list of (task exe file name, task input)

    for task_id, task_params in enumerate(tasks):
        print(task_id, task_params)

