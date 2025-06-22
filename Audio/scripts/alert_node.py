#!/usr/bin/env python3
import rospy
import os

def alert():
    rospy.init_node('alert_node', anonymous=True)
    rospy.loginfo("Alert node is running...")

    rate = rospy.Rate(0.1)

    while not rospy.is_shutdown():
        os.system('mpg123 /home/lijinzhe/are_you_okay.mp3')
        rate.sleep()

if __name__ == '__main__':
    try:
        alert()
    except rospy.ROSInterruptException:
        pass

