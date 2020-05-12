import importlib
import json
import os
from os.path import isfile

import ntpath
import socket


from os import walk
from inspect import getmembers, isfunction
import sys

from azure.servicebus import ServiceBusClient
from azure.servicebus import Message
from azure.servicebus.common.constants import ReceiveSettleMode

def _no_fail_create_queue(client: ServiceBusClient, name: str) -> bool:
    q = client.list_queues()
    for i in q:
        if i.name == name:
            return True

    return client.create_queue(name)


def task_loop(engine, task_dir: str):

    task_queue_name = 'tasks'

    module_name = ntpath.basename(task_dir)

    cwd = os.getcwd()
    print("Current working dir: {}".format(cwd))



    queue_client = engine.service_bus_client.get_queue(task_queue_name)

    #CONNECTION_STR = 'Endpoint=sb://batchcluster.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=/nfkJwwH5CMBKeWxV3Z0FxUxoDqGLPz7dy1uxL9mwLI='

    #client = ServiceBusClient.from_connection_string(CONNECTION_STR)

    #queue_client = client.get_queue(task_queue_name)


    with queue_client.get_receiver(idle_timeout=-0, mode=ReceiveSettleMode.ReceiveAndDelete, prefetch=1) as receiver:
        for message in receiver:
            print("Message: {}".format(message))

            try:
                json_data = json.loads(str(message))
                reply_to = json_data['id']
                jobid = json_data['jobid']
                taskid = json_data['taskid']

                command = json_data['command']
                input_data = json_data['params']

                print("Received task id {} from client {}".format(taskid, reply_to))

                tasks = []
                for (dirpath, dirnames, filenames) in walk(cwd +"/"+ task_dir):
                    for f in filenames:
                        if f == command:
                            print("currently found: {}".format(f))
                            if isfile(os.path.join(dirpath, f)) and not (f.endswith('__init__.py') or f.endswith('json')):
                                tasks.extend([f])
                                break
                    break

                if len(tasks) == 0:
                    raise Exception("Could not find the command ", command)

                for i in tasks[::-1]:
                    try:
                        mod_to_import = module_name + "." + os.path.splitext(i)[0]
                        print("About to import: {}".format(mod_to_import))
                        mod = importlib.import_module(mod_to_import)
                    except ImportError:
                        print("Unable to locate module: " + i)
                        return (None, None)

                out_data, error = mod.do_action(engine, input_data.split(' '))


                data = {}
                data['result'] = out_data
                data['id'] = socket.gethostname()
                data['jobid'] = jobid
                data['taskid'] = taskid
                data['error'] = error

                json_data = json.dumps(data)

                message = Message(json_data.__str__())

                _no_fail_create_queue(engine.service_bus_client, reply_to)

                queue_client = engine.service_bus_client.get_queue(reply_to)
                queue_client.send(message)
                print("sent: {}".format(json_data.__str__()))
            except Exception as inst:
                print("was not able to load json data")
                data = {}
                data['result'] = 'none'
                data['id'] = socket.gethostname()
                data['jobid'] = jobid
                data['taskid'] = taskid
                data['error'] = str(inst)

                json_data = json.dumps(data)

                message = Message(json_data.__str__())

                _no_fail_create_queue(engine.service_bus_client, reply_to)

                queue_client = engine.service_bus_client.get_queue(reply_to)
                queue_client.send(message)
                print("sent: {}".format(json_data.__str__()))


if __name__ == "__main__":

    args = ('1_task.py', 'b.txt')


    #loop = asyncio.get_event_loop()
    #loop.run_until_complete()

    task_loop('', "../tasks")