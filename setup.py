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
      'configure-pulseaudio-headset-backend.sh'
    )
    print subprocess.check_output(config_pulseaudio)

setup(
  name = 'phony',
  version = '0.9',
  description = 'A bluetooth hands-free profile headset library',
  author = 'Matthew Waddell',
  author_email = 'matt@littlecraft.io',

  namespace_packages = ['phony'],
  package_dir = {'': 'src'},
  packages = find_packages('src'),

  install_requires = [
    'pyalsaaudio'
  ],

  keywords = [
    'bluetooth',
    'handsfree',
    'hands-free',
    'hands free',
    'hfp',
    'hands free profile',
    'hands-free profile',
    'handsfree profile',
    'headset'
  ],

  cmdclass = {'install': WithPostInstall}
)