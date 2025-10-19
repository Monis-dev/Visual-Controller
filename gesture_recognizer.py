import cv2
import mediapipe as mp
import math
from collections import deque

class GestureRecognizer:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            model_complexity=0
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.landmarks = None
        
        # Gesture smoothing with deque for better performance
        self.gesture_buffer = deque(maxlen=7)
        self.last_stable_gesture = "IDLE"

    def find_hand_landmarks(self, frame):
        self.landmarks = None
        
        frame = cv2.flip(frame, 1)
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
    
    def _get_distance(self, point1, point2):
        """Calculate Euclidean distance between two points"""
        return math.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)
    
    def _get_angle(self, point1, point2, point3):
        """Calculate angle at point2 formed by point1-point2-point3"""
        radians = math.atan2(point3.y - point2.y, point3.x - point2.x) - \
                  math.atan2(point1.y - point2.y, point1.x - point2.x)
        angle = abs(math.degrees(radians))
        return angle if angle <= 180 else 360 - angle
    
    def _is_finger_extended(self, finger_name):
        """
        Check if a finger is extended using multiple criteria.
        """
        if not self.landmarks:
            return False
        
        lm = self.landmarks.landmark
        
        fingers = {
            'thumb': [1, 2, 3, 4],
            'index': [5, 6, 7, 8],
            'middle': [9, 10, 11, 12],
            'ring': [13, 14, 15, 16],
            'pinky': [17, 18, 19, 20]
        }
        
        if finger_name not in fingers:
            return False
        
        indices = fingers[finger_name]
        mcp, pip, dip, tip = [lm[i] for i in indices]
        wrist = lm[0]
        
        tip_to_wrist = self._get_distance(tip, wrist)
        pip_to_wrist = self._get_distance(pip, wrist)
        angle = self._get_angle(mcp, pip, tip)
        
        if finger_name == 'thumb':
            index_mcp = lm[5]
            thumb_extended = self._get_distance(tip, index_mcp) > self._get_distance(pip, index_mcp) * 1.1
            return thumb_extended and angle > 120
        
        is_extended = (
            tip_to_wrist > pip_to_wrist and
            angle > 140
        )
        
        return is_extended
    
    def _count_extended_fingers(self):
        """Count how many fingers are extended"""
        if not self.landmarks:
            return 0
        
        fingers = ['thumb', 'index', 'middle', 'ring', 'pinky']
        extended_count = sum(1 for finger in fingers if self._is_finger_extended(finger))
        
        return extended_count
    
    def _get_finger_states(self):
        """Get detailed state of each finger"""
        fingers = ['thumb', 'index', 'middle', 'ring', 'pinky']
        return {finger: self._is_finger_extended(finger) for finger in fingers}
    
    def get_gesture(self):
        """
        Recognize gesture based on finger states with high accuracy.
        The order of checks is important for prioritizing specific gestures.
        """
        if not self.landmarks:
            return "UNKNOWN", 0.0
        
        # Get finger states and counts
        finger_states = self._get_finger_states()
        extended_count = sum(finger_states.values())
        lm = self.landmarks.landmark

        gesture = "IDLE"
        confidence = 0.0
        
        # <<< --- NEW: PINCH GESTURE DETECTION --- >>>
        # High-priority check for a pinch gesture (thumb tip and index tip are close)
        thumb_tip = lm[self.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        pinch_distance = self._get_distance(thumb_tip, index_tip)
        
        # This threshold is based on normalized coordinates and may need tuning.
        # A smaller value means the fingers must be closer.
        pinch_threshold = 0.045

        # Condition: Thumb and index are close, and other fingers are not fully extended
        if (pinch_distance < pinch_threshold and 
            not finger_states['middle'] and 
            not finger_states['ring'] and 
            not finger_states['pinky']):
            gesture = "PINCH"
            # Confidence is higher the closer the pinch
            confidence = max(0.0, 1.0 - (pinch_distance / pinch_threshold))

        # FIST / CLOSE: All fingers curled
        elif extended_count == 0:
            gesture = "CLOSE"
            confidence = 1.0
        
        # ONE FINGER (INDEX POINTING): Only index extended
        elif extended_count == 1 and finger_states['index']:
            gesture = "POINTING"
            confidence = 1.0
        
        # TWO FINGERS: Index and middle extended (Victory/Peace sign)
        elif (extended_count == 2 and 
              finger_states['index'] and finger_states['middle']):
            gesture = "SCROLL"  # Treat as pointing for cursor control
            confidence = 0.9
        
        elif (extended_count == 2 and finger_states['pinky']):
            gesture = "COLAPS"
            confidence = 0.9

        # OPEN HAND: 4 or 5 fingers extended
        elif extended_count >= 4:
            gesture = "OPEN"
            confidence = extended_count / 5.0
        
        # --- Other cases fall back to IDLE ---
        else:
            gesture = "IDLE"
            confidence = 0.4 # Default low confidence
        
        # Add to buffer for temporal smoothing
        self.gesture_buffer.append(gesture)
        
        # Determine the most stable gesture from the buffer
        if len(self.gesture_buffer) == self.gesture_buffer.maxlen:
            # Count occurrences of each gesture in the buffer
            most_common = max(set(self.gesture_buffer), key=self.gesture_buffer.count)
            stability = self.gesture_buffer.count(most_common) / self.gesture_buffer.maxlen
            
            # Only update the stable gesture if a new one is consistently detected
            if stability > 0.6:  # Over 60% of recent frames agree
                self.last_stable_gesture = most_common
        
        # Return the last known stable gesture to prevent flickering
        return self.last_stable_gesture, confidence
    
    def get_pointer_coordinates(self, frame_shape):
        """
        Get pointer coordinates. Returns valid coordinates for 'POINTING' and 'PINCH'.
        For PINCH, it returns the midpoint of the thumb and index finger for stability.
        """
        if not self.landmarks:
            return None, None, None
        
        hand_landmarks = self.landmarks.landmark
        frame_height, frame_width, _ = frame_shape

        gesture_name, confidence = self.get_gesture()
        
        # Default to no coordinates
        coords = None

        # --- THIS IS THE KEY CHANGE ---
        # Allow cursor movement for both POINTING and PINCH gestures
        if gesture_name in ["POINTING", "PINCH"]:
            if gesture_name == "PINCH":
                # For pinch, use the midpoint between thumb and index for stability
                thumb_tip = hand_landmarks[self.mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                mid_x = (thumb_tip.x + index_tip.x) / 2
                mid_y = (thumb_tip.y + index_tip.y) / 2
                x = int(mid_x * frame_width)
                y = int(mid_y * frame_height)
                coords = (x, y)
            else: # POINTING
                # Use index finger tip for pointing
                index_finger_tip = hand_landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                x = int(index_finger_tip.x * frame_width)
                y = int(index_finger_tip.y * frame_height)
                coords = (x, y)
        
        return coords, frame_width, frame_height
    
    def get_debug_info(self):
        """Get debug information about finger states"""
        if not self.landmarks:
            return "No hand detected"
        
        finger_states = self._get_finger_states()
        extended_count = sum(finger_states.values())
        
        fingers_str = " | ".join([
            f"{finger[0].upper()}: {'✓' if extended else '✗'}"
            for finger, extended in finger_states.items()
        ])
        
        return f"Extended: {extended_count}/5 | {fingers_str}"