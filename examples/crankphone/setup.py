
from setuptools import setup, find_packages

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
    )
  ]
),
