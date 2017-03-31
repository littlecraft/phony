import time
from RPi import GPIO

reset_switch = 2
hook_switch = 3
pulses = 0

def main():
  GPIO.setmode(GPIO.BCM)

  GPIO.setup(reset_switch, GPIO.IN, pull_up_down = GPIO.PUD_UP)
  GPIO.setup(hook_switch, GPIO.IN, pull_up_down = GPIO.PUD_UP)
  GPIO.add_event_detect(reset_switch, GPIO.BOTH, callback = _io_pulsed, bouncetime = 200)
  GPIO.add_event_detect(hook_switch, GPIO.BOTH, callback = _io_pulsed, bouncetime = 200)

  while True:
    time.sleep(1000)

def _io_pulsed(channel):
  global pulses
  print '%d: channel %d changed' % (pulses, channel)
  pulses += 1

if __name__ == '__main__':
  main()
