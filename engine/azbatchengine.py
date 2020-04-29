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



import sys


sys.path.append('.')
sys.path.append('..')
sys.path.append('/mnt/resource/batch/tasks/shared/')
sys.path.append('/mnt/resource/batch/tasks/shared/engine')
sys.path.append('/mnt/resource/batch/tasks/shared/batchwrapper')
sys.path.append('/mnt/resource/batch/tasks/shared/tasks')

from batchwrapper.config import getRandomizer
from batchwrapper.config import AzureCredentials
from batchwrapper.config import ReadConfig
from batchwrapper.config import TaskConfig
from batchwrapper.config import find_file_path
import argparse
import ntpath
from engine.taskfinder import task_importer
from subprocess import *
from azure.storage.blob import BlobServiceClient

import os

class AzureBatchEngine():

    def __init__(self):

        os.chdir('/mnt/resource/batch/tasks/shared/engine')

        configuration = AzureCredentials()

        #self.account_name = configuration.getStorageAccountName()
        #self.account_key = configuration.getStorageAccountKey()
        ##self.blob_client = azureblob.BlockBlobService(account_name=self.account_name, account_key=self.account_key)

        self.storage_string = configuration.getStorageConnectionString()

        self.blob_service_client = BlobServiceClient.from_connection_string(self.storage_string)


        task = TaskConfig()

        self.container_name = task.getOutputContainer()

        paged_cont = self.blob_service_client.list_containers(name_starts_with=self.container_name)

        counter = 0
        for i in paged_cont:
            counter += 1

        if counter == 0:
            self.blob_container_client = self.blob_service_client.create_container(self.container_name)
            print("\tCreated {}... ".format(self.container_name))
        else:
            self.blob_container_client = self.blob_service_client.get_container_client(self.container_name)
            print("\tContainer {} exists already... ".format(self.container_name))


        print("Output Container to be used is: {}... ".format(self.container_name))


        self.file_list_to_upload = list()
        self.result_to_upload = ''


    def getOutputContainer(self):
        return self.container_name


    def readJsonConfigFile(self, name=''):
        if name == '':
            return
        return ReadConfig(name)

    def java_runner(self, args) -> list:

        #print("argumet is of type in java runner", type(args))
        #print("argumet is ", args)

        os.chdir('/mnt/resource/batch/tasks/shared/tasks')


        process = Popen(args, stdout=PIPE, stderr=PIPE)
        ret = []
        while process.poll() is None:
            line = process.stdout.readline()
            if line != b'' and len(line) > 0 and line.endswith(b'\n'):
                ret.append(line[:-1].decode('utf-8'))

        stdout, stderr = process.communicate()

        ret += stdout.split(b'\n')
        if stderr != b'':
            ret += stderr.split(b'\n')
        ret.remove(b'')
        return ret


    def do(self, args = []):

        #in_data = ' '.join(args[1:])
        in_data = args[1:]


        #print("setting arguments to: ", in_data)

        task_command = (args[0], in_data)

        #print("task command is: ", task_command)

        task_importer(self, "../tasks", task_command)

        #self.uploadResultData()
        self.uploadFiles()

    def do_action(self, *args):
        pass

    def addFileToUpload(self, file_name=''):


        #/mnt/batch/tasks/workitems/<job id>/job-<#>/<task id>/wd
        #/mnt/batch/tasks/shared
        name = find_file_path(file_name, "../")
        print("Found file to upload: {}".format(name))
        if name != '':
            self.file_list_to_upload.extend([name])

        print("Will upload: {}".format(self.file_list_to_upload))



    def dataToUpload(self, data: str =''):
        if data != '':
            self.result_to_upload = data

            self.uploadResultData()


    def uploadResultData(self):

        ##print("the current working directory for uploading results is: {}".format(os.getcwd()))

        filen = "result_" + getRandomizer() + ".txt"
        if self.result_to_upload != '':
            text_file = open(filen, "w")
            n = text_file.write(self.result_to_upload)
            text_file.close()
            self.addFileToUpload(filen)


    def uploadFiles(self):


        for output_file in self.file_list_to_upload:

            print('Uploading file {} to container [{}]...'.format(output_file, self.container_name))
            self.blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=ntpath.basename(output_file))

            # Upload the created file
            with open(output_file, "rb") as data:
                self.blob_client.upload_blob(data)

            self.file_list_to_upload.remove(output_file)


if __name__ == '__main__':


    print("Received input: {}".format(sys.argv[1:]))

    #all_input = sys.argv[1:];

    #data_input = ' '.join(all_input[1:])

    #foo = (all_input[0], data_input)

    #print(foo)
    #exit(1)

    engine = AzureBatchEngine()
    engine.do(sys.argv[1:])


