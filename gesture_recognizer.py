import cv2
import mediapipe as mp
import math

class GestureRecognizer:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands()
        self.mp_drawing = mp.solutions.drawing_utils
        self.landmarks = None

    def find_hand_landmarks(self, frame):
        self.landmarks = None
        
        frame = cv2.flip (frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            self.landmarks = hand_landmarks
            self.mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS
            )    

        return frame, self.landmarks
    
    def get_pointer_coordinates(self, frame_shape):
        if not self.landmarks:
            return None
        
        frame_height, frame_width, _ = frame_shape

        index_finger_tip = self.landmarks.landmark[8]

        x = int(index_finger_tip.x * frame_width)
        y = int(index_finger_tip.y * frame_height)

        return (x,y) 
    
    def get_gesture(self):
        if not self.landmarks:
            return "UNKNOWN"
        
        hand_landmarks = self.landmarks.landmark

        wrist_pt = hand_landmarks[0]
        mcp_middlefinger_base_pt = hand_landmarks[9]

        hand_scale = math.hypot(wrist_pt.x - mcp_middlefinger_base_pt.x, wrist_pt.y - mcp_middlefinger_base_pt.y)

        if hand_scale == 0:
            return "UNKNOWN"

        fingertip_indices = [8,12,16,20]
        total_normalized_distance = 0
        raw_distance = 0
        for i in fingertip_indices:
            finger_pt = hand_landmarks[i]

            raw_distance += math.hypot(wrist_pt.x - finger_pt.x, wrist_pt.y - finger_pt.y)
            
            normalized_distance = raw_distance / hand_scale
            total_normalized_distance += normalized_distance
        
        avg_normalized_distance = total_normalized_distance / len(fingertip_indices)   
        print(f"Finger landmark position from wrist:{avg_normalized_distance}")

        FIST_THRESHOLD = 4.45
        OPEN_HAND_THRESHOLD = 1.65

        if avg_normalized_distance < 3.82 and avg_normalized_distance > 3.75:
            gesture_name = "OPEN"
        elif avg_normalized_distance < 1.85 and avg_normalized_distance > 1.75:
            gesture_name = "CLOSE"
        else: 
            gesture_name = "UNKNOWN"

        return gesture_name      
