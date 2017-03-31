import time
from RPi import GPIO

pin = 26
pulse_count = 0

def main():
  GPIO.setmode(GPIO.BCM)

  GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
  GPIO.add_event_detect(pin, GPIO.BOTH, callback = _encoder_pulse, bouncetime = 200)

  while True:
    time.sleep(1000)

def _encoder_pulse(channel):
  global pulse_count
  print 'pulse %s' % pulse_count
  pulse_count += 1

if __name__ == '__main__':
  main()
