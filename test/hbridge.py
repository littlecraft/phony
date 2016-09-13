import time
from RPi import GPIO

ringer_en = 16
ringer_1 = 12
ringer_2 = 13

def main():
  GPIO.setmode(GPIO.BCM)

  GPIO.setup(ringer_1, GPIO.OUT)
  GPIO.setup(ringer_2, GPIO.OUT)
  GPIO.setup(ringer_en, GPIO.OUT)

  GPIO.output(ringer_en, 1)
  GPIO.output(ringer_1, 0)
  GPIO.output(ringer_2, 0)

  c = 0
  v = True

  while True:
    if v:
      print '%d -> +' % c
    else:
      print '%d -> -' %c

    GPIO.output(ringer_1, v)
    GPIO.output(ringer_2, not v)

    v = not v
    c += 1

    #time.sleep(0.05)
    time.sleep(2)

if __name__ == '__main__':
  main()
