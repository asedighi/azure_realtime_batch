import importlib
import sys
import os
from os.path import isfile

import ntpath

from os import walk
from inspect import getmembers, isfunction


## changing the arg to a tupple.  (task_name, taskinput)

#def task_importer(engine, task_dir, args = []):
def task_importer(engine, task_dir, args=()):

    module_name = ntpath.basename(task_dir)

    cwd = os.getcwd()
    print("current working dir: {}".format(cwd))


    tasks = []
    for (dirpath, dirnames, filenames) in walk(cwd +"/"+ task_dir):
        for f in filenames:
            if f == args[0]:
                print("currently found: {}".format(f))
                if isfile(os.path.join(dirpath, f)) and not (f.endswith('__init__.py') or f.endswith('json')):
                    tasks.extend([f])
                    break
        break




    ### we should check the task.json file against what we found here.


    """
    find task modules and import them
    """
    #tasks.reverse()

    input_data = args[1]

    for i in tasks[::-1]:
        try:
            mod_to_import = module_name + "." + os.path.splitext(i)[0]
            print("About to import: {}".format(mod_to_import))
            mod = importlib.import_module(mod_to_import)
        except ImportError:
            print("unable to locate module: " + i)
            return (None, None)

        functions_list = [o for o in getmembers(mod) if isfunction(o[1])]

        print(functions_list)

        input_data = mod.do_action(engine, input_data)


    print("The final args is: {}".format(input_data))



if __name__ == "__main__":

    args = ('1_task.py', 'b.txt')
    task_importer('', "../tasks", args)
