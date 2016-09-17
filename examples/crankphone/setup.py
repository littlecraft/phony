
from distutils.core import setup

setup(
  name = 'Crankphone',
  version = '1.0',
  description = 'Using a Raspberry Pi, turn an old hand-crank telephone into a bluetooth hands-free headset',
  author = 'Matthew Waddell',
  author_email = 'matt@littlecraft.io',

  packages = [
    'phony',
    'phony.examples',
    'phony.examples.crankphone'
  ],
  package_dir = {'': 'src'},

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
