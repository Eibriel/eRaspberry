import time
try:
    import RPi.GPIO as GPIO
except:
    print ("Run with SUDO!")

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
GPIO.output(23, 0) #OFF

while True:
    if 0:
        # Open door
        GPIO.output(23, 1) #ON
        time.sleep(5)
        GPIO.output(23, 0) #OFF