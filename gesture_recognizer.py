import cv2
import mediapipe as mp

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