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

from watson_developer_cloud import ConversationV1

from config import Config


api_url = "https://stream.watsonplatform.net/speech-to-text/api"


class session_keeper(threading.Thread):
    def __init__(self, session_id, cookies):
        self.session_id = session_id
        self.cookies = cookies
        threading.Thread.__init__(self)

    def run(self):
        while True:
            if self.session_id["session_id"] is not None:
                headers = {}
                url_base = "{}/v1/sessions/{}/recognize"
                url = url_base.format(api_url,
                                      self.session_id["session_id"])
                r = requests.get(url,
                                 headers=headers,
                                 auth=(Config.WATSON_TTS_USERNAME, Config.WATSON_TTS_PASSWORD),
                                 cookies=self.cookies)
                # print (r.text)
                r_json = None
                try:
                    r_json = r.json()
                except:
                    pass
                if r_json is not None and "session" in r_json and r_json["session"]["state"] == "initialized":
                    time.sleep(10)
                    continue

            headers = {}
            url = "{}/v1/sessions?model=es-ES_BroadbandModel".format(api_url)
            session = requests.session()
            r = session.post(url, headers=headers, auth=(Config.WATSON_TTS_USERNAME, Config.WATSON_TTS_PASSWORD))
            r_json = r.json()
            self.session_id["session_id"] = r_json["session_id"]
            self.cookies = {
                "SESSIONID": r.cookies['SESSIONID']
            }
            # print()
            print("New session id: ", self.session_id["session_id"])


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
                        if time.time()-voice_start_time > 0.2:
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
                        if time.time()-silence_start_time > 1:
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
    def __init__(self, session_id, cookies, all_data, sending_audio, sequence_id, keywords):
        threading.Thread.__init__(self)
        self.session_id = session_id
        self.cookies = cookies
        self.all_data = all_data
        self.sending_audio = sending_audio
        self.sequence_id = sequence_id
        self.keywords = keywords

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
            url_base = "{}/v1/sessions/{}/recognize?sequence_id={}&keywords={}&keywords_threshold=0.4"
            #url = "{}/v1/sessions/{}/recognize?sequence_id={}"
            url = url_base.format(api_url,
                             self.session_id["session_id"],
                             self.sequence_id[0],
                             self.keywords[0])
            # print(url)
            with requests.post(url,
                               headers=headers,
                               data=sound_loader(),
                               auth=(Config.WATSON_TTS_USERNAME, Config.WATSON_TTS_PASSWORD),
                               cookies=self.cookies,
                               stream=True) as r:
                for line in r.iter_lines():
                    pass  # print (line)


class get_text (threading.Thread):
    def __init__(self, session_id, cookies, sending_audio, sequence_id, user_text_input):
        threading.Thread.__init__(self)
        self.session_id = session_id
        self.cookies = cookies
        self.sending_audio = sending_audio
        self.sequence_id = sequence_id
        self.user_text_input = user_text_input
        self.final = False
        self.result_index = 0

    def run(self):
        headers = {}
        url_base = "{}/v1/sessions/{}/observe_result?interim_results=true&sequence_id={}"
        while True:
            if not self.sending_audio[0]:
                continue
            #    # print("Get Text: observe")
            r = None
            r_data = ""
            self.final = False
            self.result_index = 0
            url = url_base.format(api_url,
                                  self.session_id["session_id"],
                                  self.sequence_id[0])
            with requests.get(url,
                              headers=headers,
                              auth=(Config.WATSON_TTS_USERNAME, Config.WATSON_TTS_PASSWORD),
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
                        if data_json is not None and "results" not in data_json:
                            print(data_json)
                        if data_json is not None and "results" in data_json and len(data_json["results"]) > 0:
                            # print(data_json["results"][0]["alternatives"][0]["transcript"])
                            #print(data_json)
                            self.result_index = data_json["result_index"]
                            self.final = data_json["results"][0]["final"]
                            if self.final:
                                self.user_text_input["text"] = data_json["results"][0]["alternatives"][0]["transcript"]
                        r_data = ""
                    else:
                        if not dec_line.startswith("{"):
                            r_data = "{}\n{}".format(r_data, dec_line)
                #time.sleep(1)


class watson_connection(threading.Thread):
    def __init__(self, user_text_input, keywords):
        threading.Thread.__init__(self)
        self.user_text_input = user_text_input
        self.keywords = keywords
        self.conversation = ConversationV1(
                username=Config.WATSON_CON_USERNAME,
                password=Config.WATSON_CON_PASSWORD,
                version='2017-11-20')

    def run(self):
        last_user_text_input = None
        response_context = {}
        while True:
            if self.user_text_input["text"] == "" or \
              (last_user_text_input is not None and
               last_user_text_input == self.user_text_input["text"]):
                time.sleep(0.01)
                continue
            print("\nUser:{}".format(self.user_text_input["text"]))
            input_obj = {'text': self.user_text_input["text"]}
            # context_obj = Context(response_context)
            response = self.conversation.message(workspace_id=Config.WORKSPACE_ID,
                                                 input=input_obj,
                                                 context=response_context)
            # print(response)
            for out_text in response["output"]["text"]:
                print("Agente:{}".format(out_text))
            response_context = response["context"]
            if "keywords" in response_context:
                self.keywords[0] = response_context["keywords"]
            else:
                self.keywords[0] = "hola,como,estas,vengo,soy"
            last_user_text_input = self.user_text_input["text"]


threadLock = threading.Lock()
all_data = []
sending_audio = [False]
sequence_id = [rn.randint(0, 99999999)]
user_text_input = {"text": ""}
keywords = ["hola,como,estas,vengo,soy"]
session_id = {"session_id": None}
cookies = {}


# Create new threads
session_keeper_thread = session_keeper(session_id,
                                       cookies)
collect_audio_thread = collect_audio(all_data,
                                     sending_audio,
                                     sequence_id)
print("Listening")
send_audio_thread = send_audio(session_id,
                               cookies,
                               all_data,
                               sending_audio,
                               sequence_id,
                               keywords)
get_text_thread = get_text(session_id,
                           cookies,
                           sending_audio,
                           sequence_id,
                           user_text_input)
watson_connection_thread = watson_connection(user_text_input,
                                             keywords)

session_keeper_thread.start()
collect_audio_thread.start()
send_audio_thread.start()
get_text_thread.start()
watson_connection_thread.start()

session_keeper_thread.join()
collect_audio_thread.join()
send_audio_thread.join()
get_text_thread.join()
watson_connection_thread.join()
print("Exiting Main Thread")
