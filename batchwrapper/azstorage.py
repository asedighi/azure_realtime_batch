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



from batchwrapper.config import AzureCredentials

from batchwrapper.config import getRandomizer

import azure.batch.models as batchmodels
import datetime
import os
import time
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from datetime import datetime, timedelta
from azure.storage.blob import ResourceTypes, AccountSasPermissions, generate_account_sas


class AzureStorage():

    def __init__(self):

        configuration = AzureCredentials()
        random = getRandomizer()
        self.app_container_name = 'application-' + random
        self.input_container_name = 'input-' + random
        self.output_container_name = 'output-' + random

        #self.account_name = configuration.getStorageAccountName()
        #self.account_key = configuration.getStorageAccountKey()
        self.storage_string = configuration.getStorageConnectionString()


        self.location = configuration.getLocation()
        self.blob_service_client = BlobServiceClient.from_connection_string(self.storage_string)
        self.blob_container_client = None


    def getDefaultAppContainer(self):
        return self.app_container_name


    def getDefaultInputContainer(self):
        return self.input_container_name


    def getDefaultOutputContainer(self):
        return self.output_container_name

    def createInputContainer(self, container_name='', file_path=''):
        """
        Uploads a local file to an Azure Blob storage container.

        :param str container_name: The name of the Azure Blob storage container.
        :param str file_path: The local path to the file.
        :rtype: `azure.batch.models.ResourceFile`
        :return: A ResourceFile initialized with a SAS URL appropriate for Batch
        tasks.
        """
        blob_name = os.path.basename(file_path)


        paged_cont = self.blob_service_client.list_containers(name_starts_with=container_name)

        counter = 0
        for i in paged_cont:
            counter += 1

        if counter == 0:
            self.blob_container_client = self.blob_service_client.create_container(container_name)
            print("\tCreated {}... ".format(container_name))
        else:
            self.blob_container_client = self.blob_service_client.get_container_client(container_name)
            print("\tContainer {} exists already... ".format(container_name))

        print('Uploading file {} to container [{}]...'.format(file_path,
                                                              container_name))


        url = self.blob_container_client.url

        self.blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Upload the created file
        with open(file_path, "rb") as data:
            self.blob_client.upload_blob(data)

        #self.blob_client.create_blob_from_path(container_name,
        #                                        blob_name,
        #                                        file_path)

        #sas_token = generate_account_sas(
        #    self.blob_service_client.account_name,
        #    account_key=self.blob_service_client.credential.account_key,
        #    resource_types=ResourceTypes(object=True),
        #    permission=AccountSasPermissions(write=True, delete=True, read=True),
        #    expiry=datetime.utcnow() + timedelta(hours=8)
        #)
        sas_token = self._get_container_sas_token()

        #sas_token = self.blob_client.generate_blob_shared_access_signature(
        #    container_name,
        #    blob_name,
        #    permission=azureblob.BlobPermissions.READ,
        #    expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=2))

        #sas_url = self.blob_service_client.make_blob_url(container_name,
        #                                          blob_name,
        #                                          sas_token=sas_token)

        sas_url = url + "/" + blob_name + "?" + sas_token


        return batchmodels.ResourceFile(file_path=blob_name,
                                        http_url=sas_url)


    def create_output_container(self, container_name=''):

        if(container_name==''):
            container_name=self.getDefaultOutputContainer()
        blob_container_client = self.blob_service_client.create_container(container_name)
        print("\tCreated {}... ".format(container_name))

        url = blob_container_client.url

        output_container_sas_token = self._get_container_sas_token()


        #sas_url = url + "?" + output_container_sas_token

        return container_name, output_container_sas_token







    def _get_container_sas_token(self):


        sas_token = generate_account_sas(
            self.blob_service_client.account_name,
            account_key=self.blob_service_client.credential.account_key,
            resource_types=ResourceTypes(object=True),
            permission=AccountSasPermissions(write=True, delete=True, read=True),
            expiry=datetime.utcnow() + timedelta(hours=8)
        )
        return sas_token

    '''

    def _get_container_sas_token(self, container_name):
        # Instantiate a BlobServiceClient using a connection string
        from azure.storage.blob import BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(self.storage_string)

        # [START create_sas_token]
        # Create a SAS token to use to authenticate a new client
        from datetime import datetime, timedelta
        from azure.storage.blob import ResourceTypes, AccountSasPermissions, generate_account_sas

        container_sas_token = generate_account_sas(
            blob_service_client.account_name,
            account_key=blob_service_client.credential.account_key,
            resource_types=ResourceTypes(object=True),
            permission=AccountSasPermissions(write=True, delete=True, read=True),
            expiry=datetime.utcnow() + timedelta(hours=1000)
        )

        return container_sas_token
    '''



    def download_blobs_from_container(self,container_name, directory_path='./job_output'):
        """
        Downloads all blobs from the specified Azure Blob storage container.

        :param container_name: The Azure Blob storage container from which to
         download files.
        :param directory_path: The local directory to which to download the files.
        """
        print('Downloading all files from container [{}]...'.format(
            container_name))

        container_blobs = self.blob_client.list_blobs(container_name)

        for blob in container_blobs.items:
            destination_file_path = os.path.join(directory_path, blob.name)

            self.blob_client.get_blob_to_path(container_name,
                                               blob.name,
                                               destination_file_path)

            print('  Downloaded blob [{}] from container [{}] to {}'.format(
                blob.name,
                container_name,
                destination_file_path))

        print('  Download complete!')
