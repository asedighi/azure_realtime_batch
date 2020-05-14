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
import sys

import azure.batch as batch
import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels

from batchwrapper.config import AzureCredentials
from batchwrapper.config import AzureBatchConfiguration
from batchwrapper.config import getRandomizer
from batchwrapper.config import find_file_path
from batchwrapper.config import TaskManifest


sys.path.append('.')
sys.path.append('..')

import common.helpers
import time

class AzureBatch():

    def __init__(self, batch_storage_account):
        # Create a Batch service client. We'll now be interacting with the Batch
        # service in addition to Storage

        self.my_storage = batch_storage_account

        configuration = AzureCredentials()
        self.account_name = configuration.getBatchAccountName()
        self.account_key = configuration.getBatchAccountKey()
        self.account_url = configuration.getBatchAccountUrl()

        self.credentials = batchauth.SharedKeyCredentials(self.account_name,self.account_key)

        self.batch_client = batch.BatchServiceClient(self.credentials,batch_url=self.account_url)


        print("API version is: ",  self.batch_client.task.api_version)
        #self.batch_client.task.api_version = "2020-03-01.11.0"
        #print("API version is: ",  self.batch_client.task.api_version)

        batch_config = AzureBatchConfiguration()



        self.pool_count = batch_config.getNodeCount()
        self.pool_type = batch_config.getVMSize()
        self.pool_os = batch_config.getOSType()
        self.pool_publisher = batch_config.getOSPublisher()
        self.pool_os_ver = batch_config.getOSVersion()
        self.pool_engine_name = batch_config.getEngineName()

        batch_json = find_file_path("batch.json", "../")
        print("Found batch.json in: {}".format(batch_json))

        credential_json = find_file_path("credentials.json", "../")
        print("Found credentials.json in: {}".format(credential_json))

        task_json = find_file_path("task.json", "../")
        print("Found task.json in: {}".format(task_json))

        self.my_storage.addApplicationFilePath("engine/"+batch_config.getEngineName())
        self.my_storage.addApplicationFilePath("engine/taskengine.py")

        #self.my_storage.addApplicationFilePath("batchwrapper/batch.json")
        self.my_storage.addApplicationFilePath(batch_json)

        self.my_storage.addApplicationFilePath("batchwrapper/__init__.py")

        #self.my_storage.addApplicationFilePath("batchwrapper/credentials.json")
        self.my_storage.addApplicationFilePath(credential_json)
        self.my_storage.addApplicationFilePath(task_json)

        self.my_storage.addApplicationFilePath("batchwrapper/config.py")

        self.my_storage.uploadApplicationFiles()


    def use_exisiting_pool(self, pool=''):

        if pool == '':
            print("Pool Name cannot be empty")
            exit(-1)

        print('Searching for  pool [{}]...'.format(pool))

        is_there_pool = self.batch_client.pool.exists(pool)

        print("{} search came back as: {}".format(pool, is_there_pool))

        if is_there_pool == False:
            print("Pool not found ... exiting....")
            exit(-1)

        self.pool_name = pool

        return self.pool_name


    def delete_pool(self, pool=''):
        self.use_exisiting_pool(pool)
        self.batch_client.pool.delete(pool)


    def delete_all_pools(self):

        pool_list = []
        pool_paged = self.batch_client.pool.list()
        for pool_name in pool_paged:
            pool_list.append(pool_name.id)

        for n in pool_list:
            self.delete_pool(n)



    def _wait_for_ready_pool(self, pool):

        # because we want all nodes to be available before any tasks are assigned
        # to the pool, here we will wait for all compute nodes to reach idle

        pool_o = None
        pool_paged = self.batch_client.pool.list()
        for pool_s in pool_paged:
            if pool_s.id == pool:
                pool_o = pool_s
                break;

        nodes = common.helpers.wait_for_all_nodes_state(
            self.batch_client, pool_o,
            frozenset(
                (batchmodels.ComputeNodeState.start_task_failed,
                 batchmodels.ComputeNodeState.unusable,
                 batchmodels.ComputeNodeState.idle)
            )
        )
        # ensure all node are idle
        if any(node.state != batchmodels.ComputeNodeState.idle for node in nodes):
            raise RuntimeError('node(s) of pool {} not in idle state'.format(
                pool))



    def get_available_pool(self):

        pool_list = []
        pool_paged = self.batch_client.pool.list()
        for pool_name in pool_paged:
            return pool_name.id

        return ''


    def repurpose_existing_pool(self, pool='', app_resources='', input_resources='', tasks_files=''):

        self.use_exisiting_pool(pool)

        self.pool_name = pool

        if app_resources == '':
            print(
                "App resources cannot be empty.  HINT: you get this object from AzureBatchStorage.getAppResourceFiles")
            exit(-1)


        tasks = list()

        user = batchmodels.AutoUserSpecification(scope=batchmodels.AutoUserScope.pool, elevation_level=batchmodels.ElevationLevel.admin)

        job_id = self.create_a_job()

        command = ['rm -rf $AZ_BATCH_NODE_SHARED_DIR/*']

        print("Command to be executed is: {}".format(command))

        for i in range(self.pool_count):
            tasks.append(batch.models.TaskAddParameter(
                    id='{}_{}_{}'.format(str(job_id), "clean", str(i)),
                    command_line=common.helpers.wrap_commands_in_shell('linux', command),
                    user_identity=batchmodels.UserIdentity(auto_user=user))

            )

        self.batch_client.task.add_collection(job_id, tasks)

        print("Waiting for pool to become ready...")

        self._wait_for_ready_pool(self.pool_name)
        time.sleep(self.pool_count * 1.5)
        print("Back up - going to repurpose the system now")

        #we need to create a new job now
        tasks.clear()
        job_id = self.create_a_job()

        command = [
            'mkdir -p $AZ_BATCH_NODE_SHARED_DIR/batchwrapper',
            'mkdir -p $AZ_BATCH_NODE_SHARED_DIR/engine',
            'mkdir -p $AZ_BATCH_NODE_SHARED_DIR/tasks',
            'chmod 777 $AZ_BATCH_NODE_SHARED_DIR/tasks',
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/engine/'.format(self.pool_engine_name),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/engine/'.format("taskengine.py"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/batchwrapper/'.format("credentials.json"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/batchwrapper/'.format("batch.json"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/tasks'.format("task.json"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/batchwrapper/'.format("config.py"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/batchwrapper/'.format("__init__.py"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/engine/'.format("__init__.py"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/tasks/'.format("__init__.py"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/'.format("__init__.py"),
        ]

        for j in tasks_files:
            print("adding application: {}".format(j.file_path))
            command.extend(['cp -p {} $AZ_BATCH_NODE_SHARED_DIR/tasks'.format(j.file_path)])



        for i in input_resources:
            print("adding file: {}".format(i.file_path))
            command.extend(['cp -p {} $AZ_BATCH_NODE_SHARED_DIR'.format(i.file_path)])

        print("Commands to be published: {}".format(command))

        resource_meta = list()
        resource_meta.extend(app_resources)
        resource_meta.extend(tasks_files)
        resource_meta.extend(input_resources)

        user = batchmodels.AutoUserSpecification(scope=batchmodels.AutoUserScope.pool, elevation_level=batchmodels.ElevationLevel.admin)


        print("Command to be executed is: {}".format(command))
        #tasks.append(batch.models.TaskAddParameter(
        #    id='{}_{}'.format(str(job_id), "repurpose"),
        #    command_line=common.helpers.wrap_commands_in_shell('linux', command),resource_files=resource_meta,user_identity=batchmodels.UserIdentity(auto_user=user))
        #)

        #self.batch_client.task.api_version = "2020-03-01.11.0"

        #self.batch_client.task.add_collection(job_id=job_id, value=tasks)
        #self.batch_client.task.add(job_id=job_id,
        #                           task=batch.models.TaskAddParameter(
        #                                id='{}_{}'.format(str(job_id), "repurpose"),
        #                                command_line=common.helpers.wrap_commands_in_shell('linux', command),
        #                               resource_files=resource_meta,user_identity=batchmodels.UserIdentity(auto_user=user)))

        tasks = list()
        for i in range(self.pool_count):
            tasks.append(batch.models.TaskAddParameter(
                    id='{}_{}_{}'.format(str(job_id), "repurpose", str(i)),
                    command_line=common.helpers.wrap_commands_in_shell('linux', command),
                    resource_files=resource_meta,user_identity=batchmodels.UserIdentity(auto_user=user))
            )


        self.batch_client.task.add_collection(job_id, tasks)

        print("Waiting for pool to become ready after repurpose")

        self._wait_for_ready_pool(self.pool_name)
        time.sleep(self.pool_count * 1.5)

        print("Back up - ready to work now")

        return self.pool_name

    def create_pool(self, app_resources='', app_name='', input_resources='', task_files=''):

        random = getRandomizer()
        self.pool_name = 'azpool_' + random

        print('Creating pool [{}]...'.format(self.pool_name))

        if app_resources == '':
            print("App resources cannot be empty.  HINT: you get this object from AzureBatchStorage.getAppResourceFiles")
            exit(-1)

        if app_name == '':
            print("App name cannot be empty.  HINT: This python file needs to inherit from AzureBatchEngine")
            exit(-1)

        task_commands = [
            'mkdir -p $AZ_BATCH_NODE_SHARED_DIR/batchwrapper',
            'mkdir -p $AZ_BATCH_NODE_SHARED_DIR/engine',
            'mkdir -p $AZ_BATCH_NODE_SHARED_DIR/tasks',
            'chmod 777 $AZ_BATCH_NODE_SHARED_DIR/tasks',
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/engine/'.format(self.pool_engine_name),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/engine/'.format("taskengine.py"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/batchwrapper/'.format("credentials.json"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/batchwrapper/'.format("batch.json"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/tasks'.format("task.json"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/batchwrapper/'.format("config.py"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/batchwrapper/'.format("__init__.py"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/engine/'.format("__init__.py"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/tasks/'.format("__init__.py"),
            'cp -p {} $AZ_BATCH_NODE_SHARED_DIR/'.format("__init__.py"),
        ]


        for j in task_files:
            print("adding application: {}".format(j.file_path))
            task_commands.extend(['cp -p {} $AZ_BATCH_NODE_SHARED_DIR/tasks'.format(j.file_path)])


        for i in input_resources:
            print("adding file: {}".format(i.file_path))
            task_commands.extend(['cp -p {} $AZ_BATCH_NODE_SHARED_DIR'.format(i.file_path)])

        requirements_file = find_file_path("requirements.txt", ".")
        print("Found requirements.txt in: {}".format(requirements_file))

        if(requirements_file != None):
            task_commands.extend( ['/bin/bash -c "sudo yum -y install java-11-openjdk python3"', 'sudo pip3 install -r '+ requirements_file])
            ###task_commands.extend( ['curl -fSsL https://bootstrap.pypa.io/3.4/get-pip.py | python3', 'pip3 install -r '+ requirements_file])
        else:
            task_commands.extend( ['/bin/bash -c "sudo yum -y install java-11-openjdk python3"', 'sudo pip3 install -Iv azure-storage-blob==12.3.0 azure-batch==9.0.0 azure-servicebus==0.50.0'])


        print("commands to be published: {}".format(task_commands))


        # Get the node agent SKU and image reference for the virtual machine
        # configuration.
        # For more information about the virtual machine configuration, see:
        # https://azure.microsoft.com/documentation/articles/batch-linux-nodes/

        sku_to_use, image_ref_to_use = \
            common.helpers.select_latest_verified_vm_image_with_node_agent_sku(self.batch_client, self.pool_publisher, self.pool_os, self.pool_os_ver)


        user = batchmodels.AutoUserSpecification(scope=batchmodels.AutoUserScope.pool, elevation_level=batchmodels.ElevationLevel.admin)

        resource_meta = list()
        resource_meta.extend(app_resources)
        resource_meta.extend(task_files)
        resource_meta.extend(input_resources)


        new_pool = batch.models.PoolAddParameter(id=self.pool_name,
            virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(
                image_reference=image_ref_to_use,
                node_agent_sku_id=sku_to_use),
            vm_size=self.pool_type,
            target_dedicated_nodes=self.pool_count,
            max_tasks_per_node=1,
            task_scheduling_policy=batch.models.TaskSchedulingPolicy(node_fill_type=batch.models.ComputeNodeFillType.spread),
            start_task=batch.models.StartTask(
                command_line=common.helpers.wrap_commands_in_shell('linux',
                                                                   task_commands),
                user_identity=batchmodels.UserIdentity(auto_user=user),
                wait_for_success=True,
                resource_files=resource_meta),
        )

        try:
            self.batch_client.pool.add(new_pool)
        except batchmodels.batch_error.BatchErrorException as err:
            print(err)
            raise

        print("Waiting for pool to become ready after creation")
        self._wait_for_ready_pool(self.pool_name)
        time.sleep(self.pool_count * 1.5)
        print("Back up - ready to work now")

        return self.pool_name

    def delete_all_jobs(self):
        all_jobs = self.batch_client.job.list()
        for j_name in all_jobs:
            self.delete_a_job(j_name.id)


    def delete_a_job(self, id:str):
        self.batch_client.job.delete(id)


    def create_a_job(self):

        job_id = getRandomizer()

        print('Creating job [{}]...'.format(job_id))

        job = batch.models.JobAddParameter(
            id=job_id,
            on_all_tasks_complete='terminateJob',
            on_task_failure='performExitOptionsJobAction',
            pool_info=batch.models.PoolInformation(pool_id=self.pool_name))

        try:
            self.batch_client.job.add(job)
        except Exception as err:
            print(err)
            raise

        return job_id


    def add_task_to_job(self, job_id: str, task_id: int, input_command: tuple):
        """
        Adds a task for each input file in the collection to the specified job.
        :param str job_id: The ID of the job to which to add the tasks.
        :param  input_files: more like input to the exe running on the engine.
        task.py a.txt (a.txt is the input to the exe and should get passed as input
        """

        task_command = ' '.join(input_command)

        print('Adding task {} to job {}...{}'.format(task_id, job_id, task_command))

        command = ['python3 $AZ_BATCH_NODE_SHARED_DIR/engine/{} {}'.format(self.pool_engine_name, task_command)]


        tasks = []

        print("Command to be executed is: {}".format(command))

        for i in range(self.pool_count):
            tasks.append(batch.models.TaskAddParameter(
                    id='{}_{}'.format(str(job_id), str(task_id)),
                    command_line=common.helpers.wrap_commands_in_shell('linux', command),
                    )
            )
        self.batch_client.task.add_collection(job_id, tasks)


    def add_tasks_from_manifest_file(self, job_id: str, manifest_name: str):

        manifest = TaskManifest(manifest_name)

        tasks = manifest.get_tasks()

        # i have a list of (task exe file name, task input)


        for task_id, task_params in enumerate(tasks):
            self.add_task_to_job(job_id, task_id, task_params)

    def start_engine(self, job_id):
        task_id = 'engine_start'

        print('Starting engine...')

        command = ['python3 $AZ_BATCH_NODE_SHARED_DIR/engine/{}'.format(self.pool_engine_name)]


        print("Command to be executed is: {}".format(command))

        tasks = []

        for i in range(self.pool_count):
            tasks.append(batch.models.TaskAddParameter(
                    id='{}_{}'.format(str(task_id), str(i)),
                    command_line=common.helpers.wrap_commands_in_shell('linux', command),
                    )
            )
        self.batch_client.task.add_collection(job_id, tasks)

