# ui_utils.py
import cv2
import time

def draw_ui_elements(frame, state):
    """Draws all UI elements onto the frame based on the current state."""
    
    # Draw active area rectangle
    cv2.rectangle(frame, (state['x_min_bound'], state['y_min_bound']), 
                  (state['x_max_bound'], state['y_max_bound']), state['active_area_color'], 2)
    
    # Draw FPS
    cv2.putText(frame, f"FPS: {int(state['fps'])}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Draw Gesture Text
    gesture_text = f"Gesture: {state['current_gesture']}"
    if state['is_dragging']: gesture_text += " (DRAGGING)"
    if state['is_scrolling']: gesture_text += " (SCROLLING)"
    if state['is_pointer_locked']: gesture_text = "LOCKED"
    
    gesture_color = {
        "OPEN": (0, 255, 0), "CLOSE": (0, 0, 255), "PINCH": (255, 0, 255),
        "SCROLL": (255, 165, 0), "POINTING": (255, 255, 0)
    }.get(state['current_gesture'], (255, 255, 255))
    
    cv2.putText(frame, gesture_text, (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, gesture_color, 2)

    # Draw Confidence bar
    bar_width = int(200 * state['confidence'])
    cv2.rectangle(frame, (10, 75), (210, 90), (50, 50, 50), -1)
    cv2.rectangle(frame, (10, 75), (10 + bar_width, 90), gesture_color, -1)

    # Draw Velocity indicator
    velocity_bar_length = int(min(state.get('velocity', 0) * 2, 100))
    cv2.rectangle(frame, (10, 100), (110, 115), (50, 50, 50), -1)
    cv2.rectangle(frame, (10, 100), (10 + velocity_bar_length, 115), (0, 255, 255), -1)
    cv2.putText(frame, "Speed", (120, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # Draw Pointer
    if state['pointer_coords']:
        pointer_color = (0, 255, 0) # Default green
        if state['current_gesture'] == "SCROLL": pointer_color = (255, 0, 255)
        elif state['is_dragging']: pointer_color = (0, 0, 255)
        
        cv2.circle(frame, state['pointer_coords'], 10, pointer_color, -1)
        cv2.circle(frame, state['pointer_coords'], 15, pointer_color, 2)

    # Draw Status Messages
    frame_height, frame_width, _ = frame.shape
    if state['is_pointer_locked']:
        cv2.putText(frame, "POINTER LOCKED", (frame_width//2 - 150, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        cv2.putText(frame, "Show OPEN HAND to resume", (frame_width//2 - 200, 150), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    elif state['close_gesture_count'] == 1:
        time_since_close = time.time() - state['last_close_gesture_time']
        if time_since_close < config.SINGLE_CLICK_DELAY:
            cv2.putText(frame, "Waiting for 2nd fist...", (10, frame_height - 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    elif state['is_scrolling']:
        cv2.putText(frame, "Move hand UP/DOWN to scroll", (frame_width//2 - 180, frame_height - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)