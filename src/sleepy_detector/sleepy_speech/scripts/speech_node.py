#!/usr/bin/env python3
import rospy
import speech_recognition as sr
from std_msgs.msg import Bool
from sound_play.libsoundplay import SoundClient
import os
import time

class SleepySpeechNode:
    def __init__(self):
        rospy.init_node('speech_node')

        self.busy_pub = rospy.Publisher('/speech_busy',Bool,queue_size=10)
        self.recognizer = sr.Recognizer()
        self.soundhandle = SoundClient()
        self.drowsy = False
        self.speech_handling = False
        self.failed_attempts = 0
        self.max_attempts = 2
        #comment under this
        self.last_drowsy_state = False 
        self.mic_device = "plughw:4,0"  # ✅ Confirmed working mic

        self.response_pub = rospy.Publisher('/speech_response_ok', Bool, queue_size=10)
        rospy.Subscriber('/drowsiness_detected', Bool, self.drowsiness_callback)

        # Get siren path
        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.siren_path = os.path.join(script_dir, "sounds/siren.wav")

        rospy.loginfo("✅ Sleepy Speech Node started.")
        self.loop()

    def drowsiness_callback(self, msg):
        if msg.data and not self.last_drowsy_state:
            self.drowsy = True
        self.last_drowsy_state = msg.data

    def ask_and_listen(self):
        self.busy_pub.publish(True)
        try:
            # 🗣️ Prompt the user
            self.soundhandle.say("Are you okay?")
            rospy.sleep(1)

            # 🎙️ Record audio using arecord
            rospy.loginfo("🎙️ Recording with arecord...")
            record_cmd = f"arecord -D {self.mic_device} -c 1 -f S16_LE -r 16000 -d 3 /tmp/speech.wav"
            os.system(record_cmd)

            # 🔁 Play back to verify
            rospy.loginfo("🔁 Playing back captured audio...")
            

            # 🧠 Run speech recognition
            with sr.AudioFile("/tmp/speech.wav") as source:
                audio = self.recognizer.record(source)

            rospy.loginfo("🧠 Recognizing speech with Google...")
            response = self.recognizer.recognize_google(audio)
            clean_response = response.lower().strip()
            rospy.loginfo(f"🔍 Recognized: '{clean_response}'")

            if any(phrase in clean_response for phrase in ["okay", "ok", "i'm okay", "i am okay"]):
                self.soundhandle.say("Okay, stay safe.")
                self.response_pub.publish(True)
                self.failed_attempts = 0
                self.drowsy = False
            else:
                self.failed_attempts += 1
                self.response_pub.publish(False)

        except sr.UnknownValueError:
            rospy.logwarn("❌ Speech Recognition could not understand audio.")
            self.failed_attempts += 1
            self.response_pub.publish(False)

        except sr.RequestError as e:
            rospy.logerr(f"🌐 Could not reach Google Speech API: {e}")
            self.failed_attempts += 1
            self.response_pub.publish(False)

        except Exception as e:
            rospy.logerr(f"💥 Unhandled exception: {type(e).__name__}: {e}")
            self.failed_attempts += 1
            self.response_pub.publish(False)

        # 🚨 Trigger siren after 2 failed attempts
        if self.failed_attempts >= self.max_attempts:
            rospy.logwarn("⚠️ No valid response after 3 attempts. Triggering alarm.")
            rospy.loginfo(f"🔊 Playing siren: {self.siren_path}")
            self.soundhandle.playWave(self.siren_path)
            rospy.sleep(2.0)
            self.failed_attempts = 0
            self.drowsy = False
        self.busy_pub.publish(False)
        self.drowsy = False
        self.speech_handling = False

    def loop(self):
        rate = rospy.Rate(0.2)  # Every 5 seconds
        while not rospy.is_shutdown():
            if self.drowsy and not self.speech_handling:
                self.speech_handling = True
                self.ask_and_listen()
            rate.sleep()

if __name__ == '__main__':
    try:
        SleepySpeechNode()
    except rospy.ROSInterruptException:
        pass
