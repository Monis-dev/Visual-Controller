import cv2
import mediapipe as mp
import math
from utils import Utils

utils = Utils()

class GestureRecognizer:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,        # CRITICAL: Must be False for video
            max_num_hands=1,                # Only track 1 hand (faster)
            min_detection_confidence=0.5,   # Lower = faster detection
            min_tracking_confidence=0.5,    # Lower = faster tracking
            model_complexity=0 )
        self.mp_drawing = mp.solutions.drawing_utils
        self.landmarks = None

    def find_hand_landmarks(self, frame):
        self.landmarks = None
        
        frame = cv2.flip (frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]

            # smoothed_list = []
            # for i, lm in enumerate(hand_landmarks.landmark):
            #     pre_x, prev_y = self.smoothed_landmarks[i]
            #     smooth_x = utils.lerp(pre_x, lm.x, 0.3)
            #     smooth_y = utils.lerp(prev_y, lm.y, 0.3)
            #     smoothed_list.append((smooth_x, smooth_y))

            #     lm.x = smooth_x
            #     lm.y = smooth_y

            # self.smoothed_landmarks = smoothed_list    
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
        
        hand_landmarks = self.landmarks.landmark
        frame_height, frame_width, _ = frame_shape

        index_finger_tip = hand_landmarks[8]
        middle_finger_tip = hand_landmarks[12]

        index_finger_dip = hand_landmarks[7]
        middle_finger_dip = hand_landmarks[11]
        ring_finger_tip = hand_landmarks[16]
        pinky_finger_tip = hand_landmarks[20]

        gesture_name, avg_normalized_distance = self.get_gesture()  

        x = int(index_finger_tip.x * frame_width)
        y = int(index_finger_tip.y * frame_height)
        
        if avg_normalized_distance < 8.59 and avg_normalized_distance > 3.00:
            return (x,y), frame_width, frame_height
        
        return None, frame_width, frame_height
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

            raw_distance = self._calculate_angle(wrist_pt, mcp_middlefinger_base_pt, finger_pt)           
            normalized_distance = raw_distance / hand_scale
            total_normalized_distance += normalized_distance / 100 
        
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

        return gesture_name, avg_normalized_distance      

    def _calculate_angle(self, a, b, c):
        a = (a.x, a.y)
        b = (b.x, b.y)
        c = (c.x, c.y)
        
        ba = (a[0] - b[0], a[1] - b[1])
        bc = (c[0] - b[0], c[1] - b[1])
        
        dot_product = ba[0] * bc[0] + ba[1] * bc[1]
        
        mag_ba = math.hypot(ba[0], ba[1])
        mag_bc = math.hypot(bc[0], bc[1])
        
        if mag_ba == 0 or mag_bc == 0:
            return 0.0

        cosine_angle = dot_product / (mag_ba * mag_bc)
        
        cosine_angle = max(min(cosine_angle, 1.0), -1.0)

        angle = math.degrees(math.acos(cosine_angle))
        return angle