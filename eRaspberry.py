#!/usr/bin/python
# This is an example of a simple sound capture script.
#
# The script opens an ALSA pcm for sound capture. Set
# various attributes of the capture, and reads in a loop,
# Then prints the volume.
#
# To test it out, run it and shout at your microphone:


import sys
import time
import json
import numpy as np
import requests
import alsaaudio
import threading
import random as rn

from config import Config

headers = {}
api_url = "https://stream.watsonplatform.net/speech-to-text/api"
username = Config.WATSON_USERNAME
password = Config.WATSON_PASSWORD

url = "{}/v1/sessions?model=es-ES_BroadbandModel".format(api_url)
session = requests.session()
r = session.post(url, headers=headers, auth=(username, password))
r_json = r.json()
session_id = r_json["session_id"]
cookies = {
    "SESSIONID": r.cookies['SESSIONID']
}
# print()
print(session_id)


class collect_audio (threading.Thread):
    def __init__(self, all_data, sending_audio, sequence_id):
        threading.Thread.__init__(self)
        self.sending_audio = sending_audio
        self.sequence_id = sequence_id
        self.rate = 16000
        self.periodsize = 320
        # Open the device in nonblocking capture mode. The last argument could
        # just as well have been zero for blocking mode. Then we could have
        # left out the sleep call in the bottom of the loop

        #
        self.inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL)

        # Set attributes: Mono, 16000 Hz, 16 bit little endian samples
        self.inp.setchannels(1)
        self.inp.setrate(self.rate)
        self.inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)

        # The period size controls the internal number of frames per period.
        # The significance of this parameter is documented in the ALSA api.
        # For our purposes, it is suficcient to know that reads from the device
        # will return this many frames. Each frame being 2 bytes long.
        # This means that the reads below will return either 320 bytes of data
        # or 0 bytes of data. The latter is possible because we are in
        # nonblocking mode.
        self.inp.setperiodsize(self.periodsize)
        self.all_data = all_data

    def run(self):
        start_time = time.time()
        voice_start_time = None
        silence_start_time = None
        voice_last_time = time.time()
        silence_last_time = time.time()
        sending_audio = False

        while True:
            # Read data from device
            l = False
            try:
                l, data = self.inp.read()
            except alsaaudio.ALSAAudioError:
                print("ALSA Error")
            if l:
                # Sync all_data
                threadLock.acquire(True)
                self.all_data.append(data)
                # print(len(self.all_data))
                if not sending_audio and len(self.all_data) > 100:
                    del self.all_data[1]
                threadLock.release()
                np_data = np.fromstring(data, dtype=np.int16)
                if np_data.max() > 10000:
                    # print (silence_last_time - time.time())
                    if time.time() - silence_last_time > 0.01:
                        # print("No Silence")
                        if voice_start_time is None:
                            voice_start_time = time.time()
                        silence_start_time = None
                    voice_last_time = time.time()
                    if voice_start_time is not None:
                        # print("Voice duration: ", time.time()-voice_start_time)
                        if time.time()-voice_start_time > 0.5:
                            if not sending_audio:
                                print("Start sending audio")
                                sending_audio = True
                                self.sending_audio[0] = True
                        pass
                else:
                    if time.time() - voice_last_time > 3:
                        # print("No Voice")
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        voice_start_time = None
                    silence_last_time = time.time()
                    if silence_start_time is not None:
                        # print("Silence duration: ", time.time()-silence_start_time)
                        if time.time()-silence_start_time > 3:
                            if sending_audio:
                                print("Stop sending audio")
                                sending_audio = False
                                self.sending_audio[0] = False
                                threadLock.acquire(True)
                                del self.all_data[:]
                                self.sequence_id[0] = rn.randint(0, 99999999)
                                threadLock.release()
                        pass
                # print (len(data))

                # print("{} segundos - {}".format(self.all_data.shape[0]/self.rate, time.time()-start_time))
            # time.sleep(.001)


class send_audio (threading.Thread):
    def __init__(self, session_id, cookies, all_data, sending_audio, sequence_id):
        threading.Thread.__init__(self)
        self.session_id = session_id
        self.cookies = cookies
        self.all_data = all_data
        self.sending_audio = sending_audio
        self.sequence_id = sequence_id

    def run(self):
        headers = {
            'Content-Type': "audio/l16;rate=16000;channels=1;endianness=little-endian",
            "Transfer-Encoding": "chunked"
        }

        while True:
            if not self.sending_audio[0]:
                continue

            def sound_loader():
                time_start = time.time()
                while True:
                    threadLock.acquire(True)
                    if len(self.all_data) == 0:
                        threadLock.release()
                        # print("Send Audio: Waiting for data")
                        time.sleep(1)
                        continue
                    # Clean all_data
                    data_numpy = np.array([], dtype=np.int16)
                    for data in self.all_data:
                        concat = np.fromstring(data, dtype=np.int16)
                        data_numpy = np.concatenate([data_numpy, concat])
                    data = bytes(data_numpy.tostring())
                    del self.all_data[:]
                    threadLock.release()
                    # print ("Send_Audio: Sending data")
                    yield data
                    if not self.sending_audio[0]:
                        return

            # with open('Failed.raw', 'wb') as newFile:
            #    newFile.write(bytes(data_numpy.tostring()))
            # print("Send Audion: Sending {}".format(data_numpy.shape[0]))
            url = "{}/v1/sessions/{}/recognize?sequence_id={}"
            url = url.format(api_url,
                             self.session_id,
                             self.sequence_id[0])
            with requests.post(url,
                               headers=headers,
                               data=sound_loader(),
                               auth=(username, password),
                               cookies=self.cookies,
                               stream=True) as r:
                for line in r.iter_lines():
                    pass  # print (line)


class get_text (threading.Thread):
    def __init__(self, session_id, cookies, sending_audio, sequence_id):
        threading.Thread.__init__(self)
        self.session_id = session_id
        self.cookies = cookies
        self.sending_audio = sending_audio
        self.sequence_id = sequence_id
        self.result_index = False
        self.result_index = 0

    def run(self):
        headers = {}
        url = "{}/v1/sessions/{}/observe_result?interim_results=true&sequence_id={}"
        url = url.format(api_url,
                         self.session_id,
                         self.sequence_id[0])
        while True:
            if not self.sending_audio[0]:
                continue
            #    # print("Get Text: observe")
            r = None
            r_data = ""
            self.result_index = False
            self.result_index = 0
            with requests.get(url,
                              headers=headers,
                              auth=(username, password),
                              cookies=self.cookies,
                              timeout=100,
                              stream=True) as r:
                for line in r.iter_lines():
                    dec_line = line.decode()
                    if dec_line.startswith("}"):
                        r_data = "{{\n{}\n}}".format(r_data)
                        data_json = None
                        try:
                            data_json = json.loads(r_data)
                        except:
                            print("RDATA")
                            print(r_data)
                        if "results" not in data_json:
                            print(data_json)
                        if data_json is not None and "results" in data_json and len(data_json["results"]) > 0:
                            print(data_json["results"][0]["alternatives"][0]["transcript"])
                            print(data_json)
                            self.result_index = data_json["results"][0]["alternatives"]["result_index"]
                        r_data = ""
                    else:
                        if not dec_line.startswith("{"):
                            r_data = "{}\n{}".format(r_data, dec_line)
                #time.sleep(1)

threadLock = threading.Lock()
all_data = []
sending_audio = [False]
sequence_id = [rn.randint(0, 99999999)]

# Create new threads
collect_audio_thread = collect_audio(all_data, sending_audio, sequence_id)
print("Listening")
send_audio_thread = send_audio(session_id, cookies, all_data, sending_audio, sequence_id)
get_text_thread = get_text(session_id, cookies, sending_audio, sequence_id)

collect_audio_thread.start()
send_audio_thread.start()
get_text_thread.start()

collect_audio_thread.join()
send_audio_thread.join()
get_text_thread.join()
print("Exiting Main Thread")
