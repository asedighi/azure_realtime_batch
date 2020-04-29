# Azure Batch Wrapper

This project aims to provide a framework upon which the use of Azure Batch can be simpler.  The goal for the project was to enable a developer to get up and running with Azure Batch with 10 or so lines of code.  

The other purpose of this project will be to make batch more "real-time" and have it act like an interactive scheduler.




# Features:

* Get up and running with a complex Azure Batch application in minutes.  
* Create a pool, run tasks, run a workflow, delete and clean up, all with just a few function calls. 
* You dont need to create a new pool.  You can reuse the pool already created for the same job
* Repurpose an already created pool for a new job in order to reduce startup times
* the engine/task can create an output file, and submit that output file for it to be copied to Azure Blob
* Dynamically discover, order and execute tasks.  Next tasks will get picked up dynamically.
* Execute a workflow.  1_task -> 2_task -> 3_task -> n_task.py
* Pass data between tasks of a workflow
* File and data managment for input to each task and results
* Automatically uploaded results, and result files to Azure Blob
* Driver downloads results from Azure Blob (TODO)
* Error Handling (TODO)
* Configure the pool, type, etc directly by using simple config files. etc.
* Update/overwrite of config files is possible

  
# Still on the todo list:
* Method names need to be changed to comply with Python.  They are "java-style" names
* Create a package that can be imported as opposed to importing the src code
* Better documentation - src code documentation
* Clean the "common" package.  It is taken from one of the Azure examples that needs to be cleaned up
* Integrate with things like log analytics, storage, etc to move the logs, output, etc
* Pool management - increase/decrease size
* Download the results from the output bucket
* Error handling and retries for failed tasks
* Move the hardcoded params to config files - potentillay put things in batch.json



# How to use
You need to create/update credentials.json.  The template is there, but you need to add proper values

```
{
    "BATCH_ACCOUNT_NAME":"batch account name",
    "BATCH_ACCOUNT_KEY": "batch key here",
    "BATCH_ACCOUNT_URL":"https://<account name>.<eastus>.batch.azure.com",
    "STORAGE_ACCOUNT_NAME": "name here",
    "STORAGE_ACCOUNT_KEY": "key here"
}
```


The rest is just a few lines of code.  batch_driver_example.py shows how this can be accomplished.  

**Start by creating a storage interface**
```    
storage = AzureBatchStorage()
```
**Upload your input resources to the storage**
```
storage.addInputFilePath("a.txt")
storage.addInputFilePath("b.txt")
```    
**Upload the input files**
```
storage.uploadInputFiles()
```

**Upload your task file**
This file needs to implement a method called do_action(self, *argv).  This method is your main business logic.  See the end of this readme to see how tasks are managed.
```
storage.addTaskFilePath("tasks/1_task.py")
storage.addTaskFilePath("tasks/2_task.py")
```
   

**Upload your application/business logic to Storage**
```
storage.uploadTaskFiles()
```    
    
**Create a batch instance**
```
my_batch = AzureBatch(storage)
```
    
**Register your input and application files with Batch**
"getApplicationFiles" should go away in the future releases.  this method represents a background process that the user does not need to deal with.
```
app = storage.getApplicationFiles()
input_files = storage.getApplicationInputFiles()
tasks = storage.getBatchTaskFiles()
```

**Create a pool**
```
my_batch.create_pool(app_resources=app, input_resources=input_files, task_files=tasks)
```


**You can use an already existing pool**
This will keep everything intact.  Nothing will change

```
my_pool = "azpool_1558014841"
my_batch.use_exisiting_pool(my_pool)
```

**Or, you can re-purpose an existing pool with new input files/exe**
```
my_batch.repurpose_existing_pool(my_pool,app, input_files, tasks)
```

**Create a new job**
```
job_id = my_batch.create_a_job()
```

**Create a list of tasks/task input**

This feature was completely redone to allow multi-task submission via a manifest file.  
Tasks are now passed in as a tuple:
```    
args = ('1_task.py' , 'any input you want to pass to the task')
```

The above line calls 1_task.py with the 'any input you want to pass to the task' as the input to the task.   

A better example would be:
```    
args = ('1_task.py' , 'input.txt 2 34')
```

In the above case, 1_task.py gets called with the argv of "input.txt 2 34".  It is up to the task to determine 
what each of these inputs mean.   

**Run the jobs/tasks on the newly created pool**

```
my_batch.add_tasks_to_job(job_id, args)
```

**Create tasks from manifest file**
You can not submit all the tasks via a single (or multiple if you choose) manifest file.  
The example "task.json" shows an example manifest file.  All the tasks are listed in the manifest file.  The manifest 
file is executed as follows:

```
my_batch.add_tasks_from_manifest_file(job_id, "task.json")
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
The number is the order by which these tasks are executed.  1_task.py gets executed first, followed by 2_task and so on.  

The names do not need to match. As long as the files start with a number, it's good enough.  The tasks get executed in that order.  

I the task files do not have a number (say if it is only one task that needs to be executed), that's ok as well.  

taskfinder.py searchs the tasks directory for any python file.  The python file needs be like the following:

````
import os
def do_action(engine, *args):

    print('Hello world from do_action #1')
    print("the current working directory is: {}".format(os.getcwd()))

    for i in args:
        print("i need to do something to: {}".format(i))

    engine.addFileToUpload("a.txt")
    return "this is a test"
````

do_action is the method that represents the business logic, and that is the method that will get called.  The arguments (args) are past in from the client driver shown above.  

```
def do_action(self, *args):
    print('Hello world from do_action')
    print("the current working directory is: {}".format(os.getcwd()))

    for i in args:
        print("i need to do something to: {}".format(i))
    
    
    #### Do something here...
```
Once all done, you may want to upload the result file back into Azure Blob to be picked up (by the driver again perhaps).  
The return value will be passed to the next task in the list.   
```
self.addFileToUpload(<<path of some results file you want to upload>>)    
return "this is a test"
```   
For exmple, 1_task.py is called first.  the do_action method is passed a value by the driver (my_batch.add_tasks_to_job(job_id, args).

1_task.py returns a string (could be anything that makes sense to the application), and that return value will become the args value in 2_task.py.

This pattern will continue.  This allows tasks to pass value between each other.  


Task.json contains the blob container that the upload file will copy to.

