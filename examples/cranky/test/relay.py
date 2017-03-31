from RPi import GPIO
from time import sleep

p1 = 5
p2 = 6
state = 0

def setup():
  GPIO.setmode(GPIO.BCM)

  GPIO.setup(p1, GPIO.OUT)
  GPIO.setup(p2, GPIO.OUT)

  GPIO.output(p1, GPIO.LOW)
  GPIO.output(p2, GPIO.LOW)

def toggle():
  global state

  GPIO.output(p1, GPIO.LOW)
  GPIO.output(p2, GPIO.LOW)

  if state:
    GPIO.output(p1, GPIO.LOW)
    GPIO.output(p2, GPIO.HIGH)
  else:
    GPIO.output(p2, GPIO.LOW)
    GPIO.output(p1, GPIO.HIGH)

  state = not state

  sleep(0.1)

  GPIO.output(p1, GPIO.LOW)
  GPIO.output(p2, GPIO.LOW)

def main():
  setup()

  while(True):
    toggle()

    raw_input('Flip relay?')

if __name__ == '__main__':
  main()
