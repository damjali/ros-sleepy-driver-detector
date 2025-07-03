#!/usr/bin/env python3

import rospy
import speech_recognition as sr
from std_msgs.msg import Bool
from sound_play.libsoundplay import SoundClient

class SleepySpeechNode:
    def __init__(self):
        rospy.init_node('speech_node')
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.soundhandle = SoundClient()
        self.drowsy = False
        self.response_pub = rospy.Publisher('/speech_response_ok', Bool, queue_size=10)

        rospy.Subscriber('/drowsiness_detected', Bool, self.drowsiness_callback)
        rospy.loginfo("Sleepy Speech Node started.")
        self.loop()

    def drowsiness_callback(self, msg):
        self.drowsy = msg.data

    def ask_and_listen(self):
        try:
            self.soundhandle.say("Are you okay?")
            rospy.sleep(3)  # wait for speaking

            with self.microphone as source:
                rospy.loginfo("Listening for driver's response...")
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)

            response = self.recognizer.recognize_google(audio)
            rospy.loginfo(f"User said: {response}")

            # Simple check if response is okay
            if "okay" in response.lower():
                self.response_pub.publish(True)
            else:
                self.response_pub.publish(False)

        except Exception as e:
            rospy.logwarn(f"Speech error: {e}")
            self.response_pub.publish(False)

    def loop(self):
        rate = rospy.Rate(0.5)  # once every 2 seconds
        while not rospy.is_shutdown():
            if self.drowsy:
                self.ask_and_listen()
            rate.sleep()

if __name__ == '__main__':
    try:
        SleepySpeechNode()
    except rospy.ROSInterruptException:
        pass
