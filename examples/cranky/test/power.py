import sys
import time
import signal

from RPi import GPIO

ringer_en = 4

def sigint_handler(signal, frame):
  print 'SIGINT, exiting...'
  GPIO.output(ringer_en, 1)
  sys.exit(1)

def main():
  signal.signal(signal.SIGINT, sigint_handler)

  GPIO.setmode(GPIO.BCM)

  GPIO.setup(ringer_en, GPIO.OUT)

  while True:
    print 'Power on'
    GPIO.output(ringer_en, 0)

    raw_input('Turn off power?')

    print 'Power off'
    GPIO.output(ringer_en, 1)

if __name__ == '__main__':
  main()
