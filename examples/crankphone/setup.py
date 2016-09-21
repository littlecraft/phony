
import os
import subprocess

from setuptools import setup, find_packages
from setuptools.command.install import install

def script_directory():
  dir_path = os.path.dirname(os.path.realpath(__file__))
  script_dir = os.path.join(dir_path, 'scripts')
  return os.path.normpath(script_dir)

class WithPostInstall(install):
  def __init__(self, *args, **kwargs):
    install.__init__(self, *args, **kwargs)

  def run(self):
    install.run(self)
    self.post_install()

  def post_install(self):
    print 'Post installation:'

    config_pulseaudio = os.path.join(
      script_directory(),
      'bluetooth-group.sh'
    )
    print subprocess.check_output(config_pulseaudio)

setup(
  name = 'crankphone',
  version = '1.0',
  description = 'Using a Raspberry Pi, turn an old hand-crank telephone into a bluetooth hands-free headset',
  author = 'Matthew Waddell',
  author_email = 'matt@littlecraft.io',

  namespace_packages = ['phony'],
  package_dir = {'': 'src'},
  packages = find_packages('src'),

  install_requires = [
    'fysom',
    'RPI.GPIO'
  ],

  scripts = ['crankphone', 'crankphone-client'],

  data_files = [
    ('/etc/crankphone',
      [
        'deploy/crankphone.conf'
      ]
    ),
    ('/etc/systemd/system',
      [
        'deploy/systemd/crankphone.service',
        'deploy/systemd/pulseaudio.service'
      ]
    ),
    ('/etc/dbus-1/system.d',
      [
        'deploy/dbus/pulseaudio-system.conf'
      ]
    ),
    ('/etc/pulse',
      [
        'deploy/pulse/daemon.conf',
        'deploy/pulse/system.pa'
      ]
    )
  ],

  cmdclass = {'install': WithPostInstall}
),
