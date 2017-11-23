import time
import RPi.GPIO as GPIO

# Open door
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
GPIO.output(23, 0) #OFF

while True:
    if 0:
        GPIO.output(23, 1) #ON
        time.sleep(5)
        GPIO.output(23, 0) #OFF