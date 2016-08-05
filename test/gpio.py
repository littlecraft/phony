import time
from RPi import GPIO

pin = 21

def main():
  GPIO.setmode(GPIO.BCM)

  GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
  GPIO.add_event_detect(pin, GPIO.FALLING, callback = _on_hook, bouncetime = 300)
  #GPIO.add_event_detect(layout['hook_switch_pin'], GPIO.FALLING, callback = self._on_hook, bouncetime = 300)

  while True:
    time.sleep(100)

def _off_hook(channel):
  print 'off hook'

def _on_hook(channel):
  print 'on hook'

if __name__ == '__main__':
  main()
