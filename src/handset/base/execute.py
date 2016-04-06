import subprocess

def privileged(command, shell = True):
  subprocess.check_output("sudo " + command, shell = shell)