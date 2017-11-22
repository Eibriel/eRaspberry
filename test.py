import time
import alsaaudio

import numpy as np


rate = 16000
# Open the device in nonblocking capture mode. The last argument could
# just as well have been zero for blocking mode. Then we could have
# left out the sleep call in the bottom of the loop

# PCM_NORMAL
inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL)

# Set attributes: Mono, 16000 Hz, 16 bit little endian samples
inp.setchannels(1)
inp.setrate(rate)
inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)

# The period size controls the internal number of frames per period.
# The significance of this parameter is documented in the ALSA api.
# For our purposes, it is suficcient to know that reads from the device
# will return this many frames. Each frame being 2 bytes long.
# This means that the reads below will return either 320 bytes of data
# or 0 bytes of data. The latter is possible because we are in
# nonblocking mode.
inp.setperiodsize(160)

all_data = []
time_start = time.time()
while time.time()-time_start < 10:
    # Read data from device
    l = False
    try:
        l, data = inp.read()
    except alsaaudio.ALSAAudioError:
        print("ALSA Error")
    if l:
        # Sync all_data
        all_data.append(data)
    # time.sleep(.001)

data_numpy = np.array([], dtype=np.int16)
for data in all_data:
    concat = np.fromstring(data, dtype=np.int16)
    data_numpy = np.concatenate([data_numpy, concat])


with open('Test.raw', 'wb') as newFile:
    newFile.write(bytes(data_numpy.tostring()))
