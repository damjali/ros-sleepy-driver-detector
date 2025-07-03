#!/usr/bin/env python3
import rospy
from std_msgs.msg import Bool
import cv2
import mediapipe as mp
import numpy as np

class SleepyVisionNode:
    def __init__(self):
        rospy.init_node('sleepy_vision_node')
        self.pub = rospy.Publisher('/drowsiness_detected', Bool, queue_size=10)
        self.last_drowsy_state = False
        self.speech_busy = False
        rospy.Subscriber('/speech_busy', Bool, self.speech_busy_callback)

        # Mediapipe setup
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)

        # Landmark IDs
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]
        self.NOSE_TIP = 1

        # Webcam
        self.cap = cv2.VideoCapture(2)  # Change index if needed

        # Drowsiness parameters
        self.CLOSED_EAR_THRESH = 0.25
        self.CLOSED_FRAMES_THRESH = 15
        self.closed_frames = 0
        self.nose_y_baseline = None

        rospy.loginfo("✅ Sleepy Vision Node started.")
        self.run()

    def compute_ear(self, landmarks, eye_points, w, h):
        p = []
        for idx in eye_points:
            lm = landmarks.landmark[idx]
            p.append((int(lm.x * w), int(lm.y * h)))

        horiz = np.linalg.norm(np.array(p[0]) - np.array(p[3]))
        vert1 = np.linalg.norm(np.array(p[1]) - np.array(p[5]))
        vert2 = np.linalg.norm(np.array(p[2]) - np.array(p[4]))
        ear = (vert1 + vert2) / (2.0 * horiz)
        return ear
    
    def speech_busy_callback(self, msg):
        self.speech_busy = msg.data

    def run(self):
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            ret, frame = self.cap.read()
            if not ret:
                rospy.logwarn("⚠️ Failed to capture frame.")
                continue

            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            drowsy = False

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0]

                # EAR
                left_ear = self.compute_ear(landmarks, self.LEFT_EYE, w, h)
                right_ear = self.compute_ear(landmarks, self.RIGHT_EYE, w, h)
                ear = (left_ear + right_ear) / 2.0

                cv2.putText(frame, f"EAR: {ear:.2f}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

                # Eye closure logic
                if ear < self.CLOSED_EAR_THRESH:
                    self.closed_frames += 1
                else:
                    self.closed_frames = 0

                # Nose nodding
                nose = landmarks.landmark[self.NOSE_TIP]
                nose_y = nose.y

                if self.nose_y_baseline is None:
                    self.nose_y_baseline = nose_y
                    rospy.loginfo(f"📌 Nose baseline set: {self.nose_y_baseline:.4f}")

                nodding = nose_y - self.nose_y_baseline > 0.05

                if not nodding:
                    self.nose_y_baseline = 0.95 * self.nose_y_baseline + 0.05 * nose_y

                # Check drowsiness condition
                if self.closed_frames >= self.CLOSED_FRAMES_THRESH or nodding:
                    drowsy = True
                    if self.closed_frames >= self.CLOSED_FRAMES_THRESH:
                        cv2.putText(frame, "SLEEPY!", (50,100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,255), 3)
                    if nodding:
                        cv2.putText(frame, "NODDING!", (50,150), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,255), 3)

                # Draw landmarks (debug)
                for eye in [self.LEFT_EYE, self.RIGHT_EYE]:
                    for idx in eye:
                        lm = landmarks.landmark[idx]
                        x, y = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (x, y), 2, (255, 0, 0), -1)

                nose_x_px, nose_y_px = int(nose.x * w), int(nose.y * h)
                cv2.circle(frame, (nose_x_px, nose_y_px), 3, (0,255,255), -1)

            # Publish only if drowsy state changed and speech node is not busy
            if drowsy != self.last_drowsy_state:
                if not drowsy:
                    self.pub.publish(False)
                    rospy.loginfo("📣 Published drowsy status: False (reset)")
                    self.last_drowsy_state = False
                elif not self.speech_busy:
                    self.pub.publish(True)
                    rospy.loginfo("📣 Published drowsy status: True")
                    self.last_drowsy_state = True

            cv2.imshow("Sleepy Vision", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            rate.sleep()

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    try:
        SleepyVisionNode()
    except rospy.ROSInterruptException:
        pass
