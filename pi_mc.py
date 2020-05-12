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


import datetime
import os
import sys
import time

from batchwrapper.azbatchstorage import AzureBatchStorage
from batchwrapper.azbatch import AzureBatch
from driver.jobmanager import JobManager

if __name__ == '__main__':


    start_time = datetime.datetime.now().replace(microsecond=0)
    print('Start time: {}'.format(start_time))



    #Start by creating a storage interface
    storage = AzureBatchStorage()

    storage.addInputFilePath("requirements.txt")
    storage.uploadInputFiles()

    storage.addTaskFilePath("tasks/pi_runner.py")
    storage.addTaskFilePath("tasks/pi.jar")
    storage.uploadTaskFiles()

    my_batch = AzureBatch(storage)
    app = storage.getApplicationFiles()
    input_files = storage.getApplicationInputFiles()
    tasks = storage.getBatchTaskFiles()

    my_batch.delete_all_jobs()




    ## to create a pool
    #my_batch.delete_all_pools()
    #my_pool = my_batch.create_pool(app_resources=app, app_name='mcs', input_resources=input_files, task_files=tasks)

    ### to use any old pool available
    #my_pool = my_batch.get_available_pool()

    ### use a very specific pool
    my_pool = "azpool_15892385820954"
    my_batch.repurpose_existing_pool(my_pool,app, input_files, tasks)

    ### Use a specific pool without changing any configuration
    ###my_batch.use_exisiting_pool(my_pool)

    ## to delete all pools
    #my_batch.delete_all_pools()




    print("================= Using pool {} ====================".format(my_pool))

    TASK_MODULE = "pi_runner.py"
    TASK_INPUT = "java -Xmx4096m -jar pi.jar 100"


    job_id = my_batch.create_a_job()


    my_batch.start_engine(job_id)


    job_manager = JobManager("client_1", job_id)

    total = 10

    for i in range(total):
        job_manager.submit_task(str(i),TASK_MODULE, TASK_INPUT)

    result = 0
    while result < 10:
        result = job_manager.num_results_returned()
        time.sleep(1)

    print(job_manager.get_results())

    job_manager.close_job()




