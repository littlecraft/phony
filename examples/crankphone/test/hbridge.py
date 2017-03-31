import sys
import time
import signal

from RPi import GPIO

ringer_en = 4
ringer_1 = 27
ringer_2 = 22

def sigint_handler(signal, frame):
  print 'SIGINT, exiting...'
  GPIO.output(ringer_en, 1)
  sys.exit(1)

def main():
  signal.signal(signal.SIGINT, sigint_handler)

  GPIO.setmode(GPIO.BCM)

  GPIO.setup(ringer_1, GPIO.OUT)
  GPIO.setup(ringer_2, GPIO.OUT)
  GPIO.setup(ringer_en, GPIO.OUT)

  GPIO.output(ringer_en, 0)
  GPIO.output(ringer_1, 0)
  GPIO.output(ringer_2, 0)

  c = 0
  v = True

  while True:
    if v:
      print '%d -> +' % c
    else:
      print '%d -> -' %c

    GPIO.output(ringer_1, 0)
    GPIO.output(ringer_2, 0)
    GPIO.output(ringer_1, v)
    GPIO.output(ringer_2, not v)

    v = not v
    c += 1

    raw_input('Flip voltage?')

if __name__ == '__main__':
  main()
