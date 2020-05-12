# Azure Realtime Batch Wrapper
This project aims to provide a framework to add dynamic and interactive scheduling to Azure Batch.  The goal for the project is to enable a Azure Batch to do interactive task execution.  
This codebase is build atop to the exisitng Azure Batch wrapper to aide a developer to get up and running with Azure Batch with 10 or so lines of code.  

# How does it work?
The framework creates a pool based on request.  Then it uploads an 'engine' to each of the nodes.  Upon start of the engine waits for tasks to come from different clients.  
The engine takes tasks from a task queue hosted on Azure Service Bus.  The tasks are of the form ('command', 'parameters'), where the command is an executable to run.  
Once the tasks are completed, the results are sent back the client it came from using Azure Service bus.  
This interaction can continue indefinitely.  

![Azure Realtime Batch](https://github.com/asedighi/azure_realtime_batch/blob/master/Azure%20Batch%20Realtime.jpg)


# Features:
* Get up and running with a complex Azure Batch application in minutes.  
* Create a pool, run tasks, run a workflow, all with just a few function calls. 
* You dont need to create a new pool.  You can reuse the pool already created for the same job
* Repurpose an already created pool for a new job in order to reduce startup times
* Once the engine starts on the execution nodes, it will start processing tasks pending in the task queue
* Tasks queue is based on Azure Service bus - AMQP-based pub/sub messaging.  
* Tasks queue follows a FIFO de-queuing mechanism.  In other words, this scheduler is not fair!
* 'A' task is picked up from the queue, exeuted, and the result is sent back to the client via Service Bus messaging
* Each client has its own 'mailbox' to receive results
* Each task is formatted in json
* There is a new jobmanager that manages sessions: multiple job support.  
* Error Handling (TODO)
* Configure the pool, type, etc directly by using simple config files. etc.
* Update/overwrite of config files is possible
* Better job clean up.  You can delete all jobs or a single job

# Known bugs:
* Need to get ```` job_manager.close_job() ```` function to work.  Currently, it is unable to kill the listener thread.  

  
# Still on the todo list:
* Method names need to be changed to comply with Python.  They are "java-style" names
* Create a package that can be imported as opposed to importing the src code
* Better documentation - src code documentation
* Clean the "common" package.  It is taken from one of the Azure examples that needs to be cleaned up
* Integrate with things like log analytics, storage, etc to move the logs, output, etc
* Pool management - increase/decrease size
* Error handling and retries for failed tasks


# How to use (these steps remain the same with the Azure Batch Wrapper)
You need to create/update credentials.json.  The template is there, but you need to add proper values

Before you start, you need the following:
- Azure Batch Account
- Azure Storage Account
- Azure Service Bus Account

```python
{
    "BATCH_ACCOUNT_NAME":"batch account name",
    "BATCH_ACCOUNT_KEY": "batch key here",
    "BATCH_ACCOUNT_URL":"https://<account name>.<eastus>.batch.azure.com",
    "STORAGE_CONNECTION_STRING" : "<connection string here>",
    "SERVICEBUS_CONNECTION_STRING" : "<connection string here"

}
```


The rest is just a few lines of code.  batch_driver_example.py shows how this can be accomplished.  

**Start by creating a storage interface**
```python
storage = AzureBatchStorage()
```
**Upload your input resources to the storage**
```python
storage.addInputFilePath("a.txt")
storage.addInputFilePath("b.txt")
```    
**Upload the input files**
```python
storage.uploadInputFiles()
```

**Upload your task file**
This file needs to implement a method called do_action(self, *argv).  This method is your main business logic.  See the end of this readme to see how tasks are managed.
```python
storage.addTaskFilePath("tasks/1_task.py")
storage.addTaskFilePath("tasks/2_task.py")
```
   

**Upload your application/business logic to Storage**
```python
storage.uploadTaskFiles()
```    
    
**Create a batch instance**
```python
my_batch = AzureBatch(storage)
```
    
**Register your input and application files with Batch**
"getApplicationFiles" should go away in the future releases.  this method represents a background process that the user does not need to deal with.

```python
app = storage.getApplicationFiles()
input_files = storage.getApplicationInputFiles()
tasks = storage.getBatchTaskFiles()
```

**Create a pool**
```python
my_batch.create_pool(app_resources=app, input_resources=input_files, task_files=tasks)
```


**You can use an already existing pool**
This will keep everything intact.  Nothing will change

```python
my_pool = "azpool_1558014841"
my_batch.use_exisiting_pool(my_pool)
```

**Or, you can re-purpose an existing pool with new input files/exe**
```python
my_batch.repurpose_existing_pool(my_pool,app, input_files, tasks)
```

**Create a new job**
```python
job_id = my_batch.create_a_job()
```

**Create a job manager**

JobManager is essentially a session manager.  It takes a job id and a client name.  
You can have multiple jobs running, each with many tasks, by simply creating a new job manager with different client name and job id's.

```python
job_manager = JobManager("client_1", job_id)
```

This line also create a result queue on the service bus where the results appear.  

**Submit tasks**
There is no real restriction with this step.  You can submit as many tasks as you want.  I am submitting 3 boring tasks, but you can use your imagination.  

```python
total = 3
    
for i in range(total):
    job_manager.submit_task(str(i),'2_tasks.py', 'this is an input param list')
```

**Get the results**
You need to manage the number of results that you are expecting.  If you get a result for every task, you need to keep track of the number of tasks.  
Job manager collects results simply returns them.  No other steps is needed here.  This wrapper automatically collects the results.  
You do not need to wait for all the results to be returned either.  When you call ```get_results()```, you get the currently returned results.  
The next time you call ```get_results()```, you get the results returned since the last call.    

```python
    result = 0
    while result < 3:
        result = job_manager.num_results_returned()
        time.sleep(1)

    print(job_manager.get_results())
```

**Submit more tasks**
This is where the interactive part of this wrapper comes into play.  You can simply submit more tasks to be executed.  They tasks do not even need to require the same 'commnad'.
You do not need to collect the results.  You can collect all the results at once, or in batches.   The results are automatically returned by the engine the client.   

```python
    total = 4

    for i in range(total):
        job_manager.submit_task(str(i),'3_task.py', 'this is an input param list')

    result = 0
    while result < 4:
        result = job_manager.num_results_returned()
        time.sleep(1)

```


# Java support
This API now supports JAVA.   A jar file can be called from the one of the tasks files, and the output to be treated
the same as python.  
```
    jar_args = ['pi.jar']  # Any number of args to be passed to the jar file
    result = engine.java_runner(*jar_args)
```

The result comes back from the stdout and stderr to the calling program.  This api can be combined with the previous 
to call both python and Java from the same program.  (exampe to follow)



# Tasks and the tasks Module

tasks module will hold the tasks to be executed.  Currently, I have put two simple tasks in that module.  You need to create your own.
```
1_task.py 
2_task.py
```
The names do not need to match. They can be called anything.  The name of this "entry" file must be the same as the "command" passed to the task.  


The task entry file needs be like the following:

````
import os
def do_action(engine, args):

    print('Hello world from do_action #1')
    print("the current working directory is: {}".format(os.getcwd()))

    for i in args:
        print("i need to do something to: {}".format(i))

    return "result", "no error"
````

do_action is the method that represents the business logic, and that is the method that will get called.  The arguments (args) are past in from the client driver shown above.  

```
def do_action(engine, args):
    print('Hello world from do_action #2')

    for i in args:
        print("i need to do something to: {}".format(i))


    return 'this is a list of results', 'no error'
```

# Pi Monte Carlo example
Because this hasnt been done a million times!

See pi_my.py for the driver application.  We start with uploading the application files to the backend.

````python

    storage.addTaskFilePath("tasks/pi_runner.py")
    storage.addTaskFilePath("tasks/pi.jar")
    storage.uploadTaskFiles()
````  

For our purposes, both of these files are included in this repo.   

We need to either create a pool or use an exisitng pool.
````python
    my_pool = "azpool_15892490026565"
    my_batch.repurpose_existing_pool(my_pool,app, input_files, tasks)

````
We need to start the engine on the backend and create a job manager object

````python
    job_id = my_batch.create_a_job()
    my_batch.start_engine(job_id)
    job_manager = JobManager("client_1", job_id)

````
The name 'client_1' is tells the service bus where the results are going to be published to, and therefor what topic to listen to.
Now we need to submit tasks:

```python
    total = 1000
    for i in range(total):
        job_manager.submit_task(str(i),TASK_MODULE, TASK_INPUT)

```
I am submitting a 1000 tasks to the backend.  Each with the following format:
````python
    TASK_MODULE = "pi_runner.py"
    TASK_INPUT = "java -Xmx4096m -jar pi.jar 100"
````

The task module is my java wrapper on the backend, and the rest are how to kickstart a java file.  
Pi.jar takes one input, and that is an integer that tells it the number of monte Carlo iterations it needs to run (100 in our case).  

so we are running 1000*100 paths!  Potentially all in parallel.  In this case, the cluster I created is only two nodes, so it took a while! 

Here is the sample input and output to the cluster:

````json
Sent: {"id": "client_1", "jobid": "15892509695915", "taskid": "920", "command": "pi_runner.py", "params": "java -Xmx4096m -jar pi.jar 100"}

Recieved result: {"result": ["3.2"], "id": "7f1636e502064ad1af7f30ad9597863e000001", "jobid": "15892509695915", "taskid": "853", "error": "no error"}
````
I ran this a number of times with different number of tasks:
```text
# tasks	    value of pi
10	        3.192
20	        3.13
40	        3.137
100	        3.1428
1000	        3.13403999999999
```
(the fact that the value of pi goes wrong has something to do with random number generation, and not this framework)

So there are 1000 of these for this run.  The id is the hostname of the batchnode.  If there is an issue, the error will be set, and you can go back to the batch node to see what happened.  

pi_runner.py is very simple.  All the logic is in pi.jar, so pi_runner.py is just a  wrapper:

```python
def do_action(engine, args):
    print('This is a pyrunner example - b/c this hasnt been done a million times!')
    result = engine.java_runner(args)
    return result, "no error"
``` 
You can do your own error handling, but the engine handles system-level errors and sends them back.  (eg. file not found errors)