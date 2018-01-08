#!/usr/bin/python
# This is an example of a simple sound capture script.
#
# The script opens an ALSA pcm for sound capture. Set
# various attributes of the capture, and reads in a loop,
# Then prints the volume.
#
# To test it out, run it and shout at your microphone:

import os
import sys
import time
import json
import numpy as np
import requests
import alsaaudio
import threading
import random as rn


import smtplib
from email.mime.text import MIMEText

from config import Config


api_url = "https://stream.watsonplatform.net/speech-to-text/api"


class session_keeper(threading.Thread):
    def __init__(self, session_id, cookies):
        self.session_id = session_id
        self.cookies = cookies
        threading.Thread.__init__(self)

    def run(self):
        while True:
            sess_id_threadLock.acquire(True)
            session_id = self.session_id["session_id"]
            sess_id_threadLock.release()
            if session_id is not None:
                headers = {}
                url_base = "{}/v1/sessions/{}/recognize"
                url = url_base.format(api_url,
                                      session_id)
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
            r = session.post(url,
                             headers=headers,
                             auth=(Config.WATSON_TTS_USERNAME,
                                   Config.WATSON_TTS_PASSWORD))
            r_json = r.json()
            sess_id_threadLock.acquire(True)
            self.session_id["session_id"] = r_json["session_id"]
            self.cookies["SESSIONID"] = r.cookies['SESSIONID']
            sess_id_threadLock.release()
            # print()
            print("New session id: ", self.session_id["session_id"])


class collect_audio (threading.Thread):
    def __init__(self, all_data, sending_audio, sequence_id):
        threading.Thread.__init__(self)
        self.sending_audio = sending_audio
        self.sequence_id = sequence_id
        self.rate_record = Config.RATE_RECORD
        self.periodsize = 160
        # Open the device in nonblocking capture mode. The last argument could
        # just as well have been zero for blocking mode. Then we could have
        # left out the sleep call in the bottom of the loop

        #
        print(alsaaudio.pcms())
        card = "default"
        self.inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,
                                 alsaaudio.PCM_NORMAL,
                                 card)
        # Set attributes: Mono, 32000 Hz, 16 bit little endian samples
        self.inp.setchannels(1)
        self.inp.setrate(self.rate_record)
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
                if len(data) == 0:
                    threadLock.release()
                    continue
                try:
                    np_data = np.fromstring(data, dtype=np.int16)
                except:
                    # print ("Data error")
                    threadLock.release()
                    continue
                self.all_data.append(bytes(data))
                # print(len(self.all_data))
                if not sending_audio and len(self.all_data) > 100:
                    del self.all_data[1]
                threadLock.release()
                if np_data.max() > Config.MIC_TRESHOLD:
                    # print (silence_last_time - time.time())
                    if time.time() - silence_last_time > 0.01:
                        # print("No Silence")
                        if voice_start_time is None:
                            voice_start_time = time.time()
                        silence_start_time = None
                    voice_last_time = time.time()
                    if voice_start_time is not None:
                        # print("Voice duration: ", time.time()-voice_start_time)
                        if time.time() - voice_start_time > 0.2:
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
                        if time.time() - silence_start_time > 1:
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
        self.rate_send = Config.RATE_SEND
        headers = {
            'Content-Type': "audio/l16;rate={};channels=1;endianness=little-endian".format(self.rate_send),
            "Transfer-Encoding": "chunked"
        }

        while True:
            if not self.sending_audio[0]:
                time.sleep(1)
                continue
            if os.path.isfile("lock"):
                time.sleep(1)
                continue
            if os.path.isfile("using_keyboard"):
                time.sleep(1)
                continue

            def sound_loader():
                time_start = time.time()
                while True:
                    threadLock.acquire(True)
                    if len(self.all_data) == 0:
                        threadLock.release()
                        # print("Send Audio: Waiting for data")
                        time.sleep(0.1)
                        continue
                    # Clean all_data
                    data_numpy = np.array([], dtype=np.int16)
                    for data in self.all_data:
                        concat = np.fromstring(data, dtype=np.int16)
                        data_numpy = np.concatenate([data_numpy, concat])
                    data = bytes(data_numpy.tostring())
                    self.sent_sound = np.concatenate([self.sent_sound, data_numpy])
                    del self.all_data[:]
                    threadLock.release()
                    # print ("Send_Audio: Sending data")
                    yield data
                    if not self.sending_audio[0]:
                        return

            url_base = "{}/v1/sessions/{}/recognize?sequence_id={}&keywords={}&keywords_threshold=0.4"
            # url = "{}/v1/sessions/{}/recognize?sequence_id={}"
            sess_id_threadLock.acquire(True)
            keywords = self.keywords[0]
            if keywords.startswith(","):
                keywords = keywords[1:]
            url = url_base.format(api_url,
                                  self.session_id["session_id"],
                                  self.sequence_id[0],
                                  keywords)
            cookies = dict(self.cookies)
            sess_id_threadLock.release()
            # print(cookies)
            self.sent_sound = np.array([], dtype=np.int16)
            with requests.post(url,
                               headers=headers,
                               data=sound_loader(),
                               auth=(Config.WATSON_TTS_USERNAME, Config.WATSON_TTS_PASSWORD),
                               cookies=cookies,
                               stream=True) as r:
                for line in r.iter_lines():
                    # print (line)
                    pass
            with open('sent_sound_{}.raw'.format(time.time()), 'wb') as newFile:
                newFile.write(bytes(self.sent_sound.tostring()))
            # print("Send Audion: Sending {}".format(data_numpy.shape[0]))


class get_text (threading.Thread):
    def __init__(self, session_id, cookies, sending_audio, sequence_id, user_text_input, temp_text_input):
        threading.Thread.__init__(self)
        self.session_id = session_id
        self.cookies = cookies
        self.sending_audio = sending_audio
        self.sequence_id = sequence_id
        self.user_text_input = user_text_input
        self.temp_text_input = temp_text_input
        self.final = False
        self.result_index = 0

    def run(self):
        headers = {}
        url_base = "{}/v1/sessions/{}/observe_result?interim_results=true&sequence_id={}"
        while True:
            if not self.sending_audio[0]:
                continue
            # print("Get Text: observe")
            r = None
            r_data = ""
            self.final = False
            self.result_index = 0
            sess_id_threadLock.acquire(True)
            url = url_base.format(api_url,
                                  self.session_id["session_id"],
                                  self.sequence_id[0])
            cookies = dict(self.cookies)
            sess_id_threadLock.release()
            with requests.get(url,
                              headers=headers,
                              auth=(Config.WATSON_TTS_USERNAME, Config.WATSON_TTS_PASSWORD),
                              cookies=cookies,
                              timeout=100,
                              stream=True) as r:
                for line in r.iter_lines():
                    dec_line = line.decode()
                    # print (dec_line)
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
                            # print(data_json)
                            self.temp_text_input["text"] = data_json["results"][0]["alternatives"][0]["transcript"]
                            self.result_index = data_json["result_index"]
                            self.final = data_json["results"][0]["final"]
                            if self.final:
                                self.user_text_input["text"] = data_json["results"][0]["alternatives"][0]["transcript"]
                        r_data = ""
                    else:
                        if not dec_line.startswith("{"):
                            r_data = "{}\n{}".format(r_data, dec_line)
                # time.sleep(1)


class watson_connection(threading.Thread):
    def __init__(self, sending_audio, user_text_input, watson_text_output, keywords):
        threading.Thread.__init__(self)
        self.sending_audio = sending_audio
        self.user_text_input = user_text_input
        self.watson_text_output = watson_text_output
        self.keywords = keywords

    def run(self):
        first_time = True
        last_user_text_input = None
        response_context = {}
        while True:
            if os.path.isfile("using_keyboard"):
                status_keyboard_path = "status_keyboard.json"
                if os.path.exists(status_keyboard_path):
                    with open(status_keyboard_path, encoding='utf-8') as data_file:
                        try:
                            data = json.load(data_file)
                        except:
                            continue
                    print(status_keyboard_path)
                    self.user_text_input["text"] = data["message"]
                    os.remove(status_keyboard_path)
                else:
                    continue
            # else:
            if os.path.isfile("lock"):
                self.sending_audio[0] = False
                self.user_text_input["text"] = ""
                self.watson_text_output["text"] = []
                response_context = {}
                time.sleep(0.1)
                continue
            if self.user_text_input["text"] == "" or \
               (last_user_text_input is not None and
               last_user_text_input == self.user_text_input["text"]):
                time.sleep(0.01)
                continue
            print("\nUser:{}".format(self.user_text_input["text"]))
            input_obj = {'text': self.user_text_input["text"]}

            headers = {
                'Content-Type': "application/json"
            }
            url_base = "https://gateway.watsonplatform.net/conversation/api/v1/workspaces/{}/message?version=2017-05-26"
            url = url_base.format(Config.WORKSPACE_ID)
            if first_time:
                data = {}
                first_time = False
                r = requests.post(url,
                                  headers=headers,
                                  data=json.dumps(data),
                                  auth=(Config.WATSON_CON_USERNAME,
                                        Config.WATSON_CON_PASSWORD))
                try:
                    response = r.json()
                except:
                    response = None
                response_context = response["context"]
            data = {
                "input": input_obj,
                "context": response_context
            }
            r = requests.post(url,
                              headers=headers,
                              data=json.dumps(data),
                              auth=(Config.WATSON_CON_USERNAME,
                                    Config.WATSON_CON_PASSWORD))
            try:
                response = r.json()
            except:
                response = None

            if "output" not in response:
                print(response)
                continue
            for out_text in response["output"]["text"]:
                print("Agente:{}".format(out_text))
            self.watson_text_output["text"] = response["output"]["text"]
            response_context = response["context"]
            if "keywords" in response_context:
                self.keywords[0] = response_context["keywords"]
            else:
                self.keywords[0] = "hola,como,estas,vengo,soy"
            last_user_text_input = self.user_text_input["text"]

            if "send_notification" in response_context:
                del[response_context["send_notification"]]
                nombre_anfitrion = response_context.get("nombre_anfitrion")
                nombre_invitado = response_context.get("nombre_invitado")
                print("nombre_anfitrion", nombre_anfitrion)
                print("nombre_invitado", nombre_invitado)
                msg_to = Config.EMAILS.get(nombre_anfitrion)
                print("mail anfitrion", msg_to)
                if msg_to is None:
                    msg_to = Config.EMAIL_DEFAULT
                    print("mail default", msg_to)
                print(msg_to)
                print("Sending notification!")
                # Open a plain text file for reading.
                # For this example, assume that
                # the text file contains only ASCII characters.
                if nombre_invitado is not None:
                    msg_body = "{} está en la puerta!!".format(nombre_invitado)
                else:
                    msg_body = "Hay alguien en la puerta!"
                msg = MIMEText(msg_body)

                msg_from = "mg54_puerta@eibriel.com"
                if Config.EMAIL_TEST:
                    msg_to = ["eibriel@eibriel.com"]
                    print("mail test", msg_to)

                user = Config.EMAIL_USER
                pwd = Config.EMAIL_PASS
                msg['Subject'] = msg_body
                msg['From'] = msg_from
                msg['To'] = ", ".join(msg_to)

                if not Config.EMAIL_DRY:
                    # Send the message via our own SMTP server,
                    # but don't include the
                    # envelope header.
                    smtpserver = smtplib.SMTP('mail.eibriel.com', 587)
                    smtpserver.ehlo()
                    smtpserver.starttls()
                    smtpserver.ehlo
                    smtpserver.login(user, pwd)
                    smtpserver.sendmail(msg_from, msg_to, msg.as_string())
                    smtpserver.quit()
                else:
                    print(msg)
            # time.sleep(1.0)



class save_status(threading.Thread):
    def __init__(self, sending_audio, user_text_input, temp_text_input, watson_text_output):
        threading.Thread.__init__(self)
        self.sending_audio = sending_audio
        self.user_text_input = user_text_input
        self.temp_text_input = temp_text_input
        self.watson_text_output = watson_text_output

    def run(self):
        # Sending Audio?
        while True:
            # print("Status")
            # print(self.sending_audio[0])
            data = {
                "sending_audio": self.sending_audio[0],
                "user_text_input": self.user_text_input["text"],
                "temp_text_input": self.temp_text_input["text"],
                "watson_text_output": self.watson_text_output["text"]
            }
            if os.path.isfile("using_keyboard"):
                data["sending_audio"] = False
            with open("status.json", 'w', encoding='utf-8') as status_file:
                json.dump(data, status_file, sort_keys=True, indent=4, separators=(',', ': '))
            #if len(self.watson_text_output["text"]) > 0:
            #    lala()
            time.sleep(0.1)


threadLock = threading.Lock()
sess_id_threadLock = threading.Lock()
all_data = []
sending_audio = [False]
sequence_id = [rn.randint(0, 99999999)]
user_text_input = {"text": ""}
temp_text_input = {"text": ""}
watson_text_output = {"text": []}
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
                           user_text_input,
                           temp_text_input)
watson_connection_thread = watson_connection(sending_audio,
                                             user_text_input,
                                             watson_text_output,
                                             keywords)
save_status_thread = save_status(sending_audio,
                                 user_text_input,
                                 temp_text_input,
                                 watson_text_output)

session_keeper_thread.start()
collect_audio_thread.start()
send_audio_thread.start()
get_text_thread.start()
watson_connection_thread.start()
save_status_thread.start()

session_keeper_thread.join()
collect_audio_thread.join()
send_audio_thread.join()
get_text_thread.join()
watson_connection_thread.join()
save_status_thread.join()
print("Exiting Main Thread")
