from azure.servicebus import Message
import json
from batchwrapper.config import AzureCredentials
from azure.servicebus.aio import ServiceBusClient as AsyncClient
from azure.servicebus import ServiceBusClient as SyncClient
import threading
from azure.servicebus.common.constants import ReceiveSettleMode



class JobManager():

    def __init__(self, name: str, job_id: str):

        self.name = name
        self.job_id = job_id
        configuration = AzureCredentials()

        self.conn_string = configuration.get_service_bus_connection_string()


        self.client = SyncClient.from_connection_string(self.conn_string)
        self._no_fail_create_queue(self.client, "tasks")
        self.queue_client = self.client.get_queue("tasks")

        self._no_fail_create_queue(self.client,self.name)

        self.results = list()

        self.result_thread = threading.Thread(target=self.result_collector)
        self.result_thread.start()

    def result_collector(self):
        servicebus_client = SyncClient.from_connection_string(conn_str=self.conn_string)

        self._no_fail_create_queue(servicebus_client, self.name)
        queue_client = servicebus_client.get_queue(self.name)

        with queue_client.get_receiver(idle_timeout=0, mode=ReceiveSettleMode.ReceiveAndDelete, prefetch=1) as receiver:
            # Receive messages as a continuous generator
            for message in receiver:
                print("Recieved result: {}".format(message))
                json_data = json.loads(str(message))
                self.results.append(json_data)



    def _no_fail_create_queue(self, client: SyncClient, name: str) -> bool:
        q = client.list_queues()
        for i in q:
            if i.name == name:
                return True

        return client.create_queue(name)


    def submit_task(self, task_id: str, command: str, params: str):

        with self.queue_client.get_sender() as sender:
            data = {}
            data['id'] = self.name
            data['jobid'] = self.job_id
            data['taskid'] = task_id
            data['command'] = command
            data['params'] = params
            json_data = json.dumps(data)

            message = Message(json_data.__str__())
            sender.send(message)
            print("sent: {}".format(json_data.__str__()))
            # message = Message("not json test")
            # sender.send(message)


    def num_results_returned(self):
        return len(self.results)


    def get_results(self):
        r = self.results.copy()
        self.results.clear()
        return r

    def close_job(self):
        self.result_thread.join()