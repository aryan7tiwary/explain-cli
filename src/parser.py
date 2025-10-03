import shlex

def tokenize_command(command_string):
    return shlex.split(command_string)
