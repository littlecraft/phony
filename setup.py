
from distutils.core import setup

setup(
  name = 'phony',
  version = '0.9',
  description = 'A bluetooth hands-free profile headset library',
  author = 'Matthew Waddell',
  author_email = 'matt@littlecraft.io',

  packages = [
    'phony',
    'phony.audio',
    'phony.base',
    'phony.bluetooth',
    'phony.bluetooth.adapters',
    'phony.bluetooth.profiles',
    'phony.bluetooth.profiles.handsfree',
    'phony.io'
  ],
  package_dir = {'': 'src'}
),
