import time
from RPi import GPIO

pin = 21
on_count = 0
off_count = 0

def main():
  GPIO.setmode(GPIO.BCM)

  GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
  GPIO.add_event_detect(pin, GPIO.BOTH, callback = _hook_switch_changed, bouncetime = 200)

  while True:
    time.sleep(100)

def _hook_switch_changed(channel):
  global on_count
  global off_count

  time.sleep(0.1)

  on_off = ''
  if not GPIO.input(channel):
    on_count += 1
    on_off = 'on'
  else:
    off_count += 1
    on_off = 'off'

  print 'hook switch %s (%d/%d)' % (on_off, on_count, off_count)

def _hook_switch_falling(channel):
  pass

if __name__ == '__main__':
  main()
