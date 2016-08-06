import time
from RPi import GPIO

pin = 21
on_count = 0
off_count = 0

def main():
  GPIO.setmode(GPIO.BCM)

  GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
  GPIO.add_event_detect(pin, GPIO.BOTH, callback = _hook_switch_changed, bouncetime = 300)

  while True:
    time.sleep(100)

def _hook_switch_changed(channel):
  global on_count
  global off_count

  if GPIO.input(channel):
    print 'off hook: %s' % off_count
    off_count += 1
  else:
    print 'on hook: %s' % on_count
    on_count += 1

if __name__ == '__main__':
  main()
