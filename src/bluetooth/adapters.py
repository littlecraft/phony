import base.execute
from base.log import ClassLogger

class Bluez4(ClassLogger):
  __hci_device = None

  def __init__(self, hci_device):
    ClassLogger.__init__(self)
    self.__hci_device = hci_device

  def device(self):
    return self.__hci_device

  def enable_visibility(self):
    self.__exec("piscan")

  def disable_visibility(self):
    self.__exec("noscan")

  def __exec(self, fmt, *args):
    command = "hciconfig " + self.__hci_device + " " + fmt % args
    self.log().debug('Running: ' + command)
    base.execute.privileged(command, shell = True)