import cv2 
import time
import threading
import queue
import numpy as np
from collections import deque
from gesture_recognizer import GestureRecognizer
from computer_controller import ComputerController

print("Attempting to connect to camera")
cap = cv2.VideoCapture(1)

recognizer = GestureRecognizer()
controller = ComputerController()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# === ENHANCED STABILITY SETTINGS ===

# 1. EXPONENTIAL SMOOTHING (Primary smoothing)
smoothing_factor = 0.3  # Lower = smoother but slower (0.1-0.5)

# 2. MOVING AVERAGE FILTER (Secondary smoothing)
position_buffer_size = 5  # Average of last N positions
position_buffer_x = deque(maxlen=position_buffer_size)
position_buffer_y = deque(maxlen=position_buffer_size)

# 3. KALMAN-LIKE FILTERING (Advanced smoothing)
use_kalman_filter = True
kalman_process_variance = 0.01  # How much we trust hand movement
kalman_measurement_variance = 0.1  # How much we trust sensor

# 4. DEADZONE (Ignore tiny movements)
DEADZONE_PIXELS = 3  # Ignore movements smaller than this

# 5. VELOCITY LIMITING (Prevent sudden jumps)
MAX_VELOCITY = 80  # Maximum pixels per frame

# 6. ADAPTIVE SMOOTHING (Smooth more when hand is still)
use_adaptive_smoothing = True
velocity_threshold_for_adaptive = 20  # pixels/frame

# Other settings
last_gesture = "IDLE"
prev_frame_time = 0
prev_x, prev_y = 0, 0
last_raw_x, last_raw_y = 0, 0
is_pointer_locked = False

last_click_time = 0
CLICK_COOLDOWN = 0.3

last_close_gesture_time = 0
close_gesture_count = 0
DOUBLE_CLICK_WINDOW = 0.6
SINGLE_CLICK_DELAY = 0.7

is_dragging = False
is_scrolling = False
scroll_start_y = 0
last_scroll_time = 0
SCROLL_SENSITIVITY = 30
SCROLL_DEADZONE = 0.01

FRAME_REDUCTION = 0.2
running = True

# Kalman filter state
kalman_x = 0
kalman_y = 0
kalman_p_x = 1
kalman_p_y = 1

mouse_queue = queue.Queue(maxsize=2)

def moving_average_filter(buffer, new_value):
    """Apply moving average smoothing"""
    buffer.append(new_value)
    return sum(buffer) / len(buffer)

def kalman_filter(estimate, estimate_error, measurement, measurement_error, process_variance):
    """Simple 1D Kalman filter for position smoothing"""
    # Prediction
    prediction = estimate
    prediction_error = estimate_error + process_variance
    
    # Update
    kalman_gain = prediction_error / (prediction_error + measurement_error)
    new_estimate = prediction + kalman_gain * (measurement - prediction)
    new_estimate_error = (1 - kalman_gain) * prediction_error
    
    return new_estimate, new_estimate_error

def apply_velocity_limit(new_x, new_y, old_x, old_y, max_velocity):
    """Limit maximum velocity to prevent jumps"""
    dx = new_x - old_x
    dy = new_y - old_y
    distance = np.sqrt(dx**2 + dy**2)
    
    if distance > max_velocity:
        # Scale down to max velocity
        scale = max_velocity / distance
        new_x = old_x + dx * scale
        new_y = old_y + dy * scale
    
    return new_x, new_y

def apply_deadzone(new_x, new_y, old_x, old_y, deadzone):
    """Ignore movements smaller than deadzone"""
    dx = abs(new_x - old_x)
    dy = abs(new_y - old_y)
    
    if dx < deadzone and dy < deadzone:
        return old_x, old_y  # No movement
    return new_x, new_y

def adaptive_smoothing_factor(velocity, base_factor, threshold):
    """Increase smoothing when hand is moving slowly"""
    if velocity < threshold:
        # Hand is still - use stronger smoothing
        return max(0.1, base_factor * 0.5)
    else:
        # Hand is moving - use normal smoothing
        return base_factor

def mouse_controller_thread():
    while running:
        try:
            x, y = mouse_queue.get(timeout=0.05)
            if not is_dragging and not is_pointer_locked and not is_scrolling:
                controller.point_movement(int(x), int(y))
        except queue.Empty:
            continue
        except Exception:
            break

mouse_thread = threading.Thread(target=mouse_controller_thread, daemon=True)
mouse_thread.start()

if not cap.isOpened():
    print("Error: Could not connect to the camera")
else:
    print("Success! Camera stream is open.")
    print("\n=== ENHANCED STABILITY MODE ===")
    print("Controls:")
    print("  👆 POINTING → Move cursor")
    print("  🤏 PINCH → Drag")
    print("  ✋ OPEN HAND → Left Click")
    print("  ✊ FIST (once) → Right Click")
    print("  ✊ FIST (twice) → Double Left Click")
    print("  ☝️ THREE FINGERS → Scroll")
    print("\nStability Features:")
    print(f"  • Exponential smoothing: {smoothing_factor}")
    print(f"  • Moving average: {position_buffer_size} frames")
    print(f"  • Kalman filter: {'ON' if use_kalman_filter else 'OFF'}")
    print(f"  • Deadzone: {DEADZONE_PIXELS}px")
    print(f"  • Velocity limit: {MAX_VELOCITY}px/frame")
    print(f"  • Adaptive smoothing: {'ON' if use_adaptive_smoothing else 'OFF'}\n")
    
    try:
        while True:
            success, frame = cap.read()
            if not success: 
                continue

            new_frame_time = time.time()
            fps = 1 / (new_frame_time - prev_frame_time) if prev_frame_time > 0 else 0
            prev_frame_time = new_frame_time     

            processed_frame, landmarks = recognizer.find_hand_landmarks(frame)
            frame_height, frame_width, _ = processed_frame.shape

            if not is_pointer_locked and controller.check_for_manual_failsafe():
                is_pointer_locked = True
                if is_dragging:
                    controller.end_drag()
                    is_dragging = False
                if is_scrolling:
                    is_scrolling = False
                print("⏸ PAUSED")

            current_gesture, confidence = recognizer.get_gesture()
            current_time = time.time()

            x_min_bound = int(FRAME_REDUCTION * frame_width)
            y_min_bound = int(FRAME_REDUCTION * frame_height)
            x_max_bound = int(frame_width - (FRAME_REDUCTION * frame_width))
            y_max_bound = int(frame_height - (FRAME_REDUCTION * frame_height))

            if not is_pointer_locked:
                active_area_color = (255, 255, 0)
                
                # SCROLL HANDLING
                if landmarks:
                    if current_gesture == "SCROLL":
                        if not is_scrolling:
                            is_scrolling = True
                            scroll_start_y = landmarks.landmark[12].y
                            last_scroll_time = current_time
                            print("📜 Scroll started")
                        else:
                            current_scroll_y = landmarks.landmark[12].y
                            delta_y = scroll_start_y - current_scroll_y
                            
                            if abs(delta_y) > SCROLL_DEADZONE and (current_time - last_scroll_time) > 0.05:
                                scroll_amount = int(delta_y * SCROLL_SENSITIVITY)
                                if scroll_amount != 0:
                                    controller.scroll(scroll_amount)
                                    last_scroll_time = current_time
                                scroll_start_y = current_scroll_y
                    
                    elif is_scrolling:
                        is_scrolling = False
                        scroll_start_y = 0
                        print("📜 Scroll ended")
                
                # === CURSOR MOVEMENT WITH STABILITY ===
                if not is_scrolling and landmarks:
                    pointer_coords, _, _ = recognizer.get_pointer_coordinates(processed_frame.shape)
                    
                    if pointer_coords:
                        raw_x, raw_y = pointer_coords
                        
                        # Map to screen coordinates
                        screen_x = np.interp(raw_x, (x_min_bound, x_max_bound), (0, controller.screen_width))
                        screen_y = np.interp(raw_y, (y_min_bound, y_max_bound), (0, controller.screen_height))
                        
                        # === STABILITY PIPELINE ===
                        
                        # Step 1: Moving Average Filter
                        screen_x = moving_average_filter(position_buffer_x, screen_x)
                        screen_y = moving_average_filter(position_buffer_y, screen_y)
                        
                        # Step 2: Kalman Filter (optional)
                        if use_kalman_filter:
                            kalman_x, kalman_p_x = kalman_filter(
                                kalman_x, kalman_p_x, screen_x, 
                                kalman_measurement_variance, kalman_process_variance
                            )
                            kalman_y, kalman_p_y = kalman_filter(
                                kalman_y, kalman_p_y, screen_y,
                                kalman_measurement_variance, kalman_process_variance
                            )
                            screen_x, screen_y = kalman_x, kalman_y
                        
                        # Step 3: Velocity Limiting
                        screen_x, screen_y = apply_velocity_limit(
                            screen_x, screen_y, prev_x, prev_y, MAX_VELOCITY
                        )
                        
                        # Step 4: Calculate velocity for adaptive smoothing
                        velocity = np.sqrt((screen_x - prev_x)**2 + (screen_y - prev_y)**2)
                        
                        # Step 5: Adaptive Smoothing Factor
                        if use_adaptive_smoothing:
                            current_smoothing = adaptive_smoothing_factor(
                                velocity, smoothing_factor, velocity_threshold_for_adaptive
                            )
                        else:
                            current_smoothing = smoothing_factor
                        
                        # Step 6: Apply Exponential Smoothing
                        current_x = prev_x + (screen_x - prev_x) * current_smoothing
                        current_y = prev_y + (screen_y - prev_y) * current_smoothing
                        
                        # Step 7: Apply Deadzone
                        current_x, current_y = apply_deadzone(
                            current_x, current_y, prev_x, prev_y, DEADZONE_PIXELS
                        )
                        
                        # Move cursor
                        if not is_dragging:
                            try: 
                                mouse_queue.put_nowait((current_x, current_y))
                            except queue.Full: 
                                pass
                        else:
                            controller.point_movement(int(current_x), int(current_y))
                        
                        prev_x, prev_y = current_x, current_y
                        last_raw_x, last_raw_y = screen_x, screen_y
                        
                        # Visual feedback
                        if current_gesture == "SCROLL":
                            pointer_color = (255, 0, 255)
                        elif is_dragging:
                            pointer_color = (0, 0, 255)
                        else:
                            pointer_color = (0, 255, 0)
                        
                        cv2.circle(processed_frame, pointer_coords, 10, pointer_color, -1)
                        cv2.circle(processed_frame, pointer_coords, 15, pointer_color, 2)
                        
                        # Show velocity indicator
                        velocity_bar_length = int(min(velocity * 2, 100))
                        cv2.rectangle(processed_frame, (10, 100), (110, 115), (50, 50, 50), -1)
                        cv2.rectangle(processed_frame, (10, 100), (10 + velocity_bar_length, 115), (0, 255, 255), -1)
                        cv2.putText(processed_frame, "Speed", (120, 112), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

                # DRAG HANDLING
                if not is_scrolling:
                    if current_gesture == "PINCH" and last_gesture != "PINCH":
                        if not is_dragging:
                            controller.start_drag()
                            is_dragging = True
                            print("🖱 Drag started")
                    
                    elif current_gesture != "PINCH" and is_dragging:
                        controller.end_drag()
                        is_dragging = False
                        print("🖱 Drag ended")
                
                # CLICK HANDLING
                if not is_dragging and not is_scrolling and confidence > 0.7:
                    
                    if current_gesture == "OPEN" and last_gesture != "OPEN":
                        if (current_time - last_click_time) > CLICK_COOLDOWN:
                            controller.left_click()
                            last_click_time = current_time
                            print("🖱 Left Click")
                    
                    elif current_gesture == "CLOSE" and last_gesture != "CLOSE":
                        time_since_last_close = current_time - last_close_gesture_time
                        
                        if time_since_last_close < DOUBLE_CLICK_WINDOW and close_gesture_count == 1:
                            controller.double_left_click()
                            last_click_time = current_time
                            close_gesture_count = 0
                            last_close_gesture_time = 0
                            print("🖱🖱 Double Left Click")
                        else:
                            close_gesture_count = 1
                            last_close_gesture_time = current_time
                    elif current_gesture == "COLAPS" and last_gesture != "COLAPS":
                        controller.colaps()
                        print("Closing folder")
                if close_gesture_count == 1:
                    time_since_close = current_time - last_close_gesture_time
                    if time_since_close > SINGLE_CLICK_DELAY:
                        controller.right_click()
                        last_click_time = current_time
                        close_gesture_count = 0
                        last_close_gesture_time = 0
                        print("🖱 Right Click")
            
            else:  # LOCKED
                active_area_color = (0, 0, 255)
                
                cv2.putText(processed_frame, "POINTER LOCKED", 
                           (frame_width//2 - 150, 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                cv2.putText(processed_frame, "Show OPEN HAND to resume", 
                           (frame_width//2 - 200, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

                if current_gesture == "OPEN" and confidence > 0.8:
                    center_x = controller.screen_width // 2
                    center_y = controller.screen_height // 2
                    controller.point_movement(center_x, center_y)
                    
                    if landmarks:
                        pointer_coords, _, _ = recognizer.get_pointer_coordinates(processed_frame.shape)
                        if pointer_coords:
                            raw_x, raw_y = pointer_coords
                            prev_x = np.interp(raw_x, (x_min_bound, x_max_bound), (0, controller.screen_width))
                            prev_y = np.interp(raw_y, (y_min_bound, y_max_bound), (0, controller.screen_height))
                            
                            # Reset filters
                            position_buffer_x.clear()
                            position_buffer_y.clear()
                            kalman_x, kalman_y = prev_x, prev_y
                            kalman_p_x, kalman_p_y = 1, 1
                    
                    is_pointer_locked = False
                    is_scrolling = False
                    last_click_time = current_time
                    close_gesture_count = 0
                    last_close_gesture_time = 0
                    print("▶ RESUMED")

            last_gesture = current_gesture

            # VISUAL FEEDBACK
            cv2.rectangle(processed_frame, (x_min_bound, y_min_bound), 
                         (x_max_bound, y_max_bound), active_area_color, 2)
            
            cv2.putText(processed_frame, f"FPS: {int(fps)}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            gesture_text = f"Gesture: {current_gesture}"
            if is_dragging: 
                gesture_text += " (DRAGGING)"
            if is_scrolling: 
                gesture_text += " (SCROLLING)"
            if is_pointer_locked: 
                gesture_text = "LOCKED"
            
            gesture_color = {
                "OPEN": (0, 255, 0),
                "CLOSE": (0, 0, 255),
                "PINCH": (255, 0, 255),
                "SCROLL": (255, 165, 0),
                "POINTING": (255, 255, 0)
            }.get(current_gesture, (255, 255, 255))
            
            cv2.putText(processed_frame, gesture_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, gesture_color, 2)
            
            # Confidence bar
            bar_width = int(200 * confidence)
            cv2.rectangle(processed_frame, (10, 75), (210, 90), (50, 50, 50), -1)
            cv2.rectangle(processed_frame, (10, 75), (10 + bar_width, 90), gesture_color, -1)
            
            if close_gesture_count == 1:
                remaining_time = SINGLE_CLICK_DELAY - (current_time - last_close_gesture_time)
                if remaining_time > 0:
                    cv2.putText(processed_frame, "Waiting for 2nd fist...", 
                               (10, frame_height - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            if is_scrolling:
                cv2.putText(processed_frame, "Move hand UP/DOWN to scroll", 
                           (frame_width//2 - 180, frame_height - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
            
            cv2.imshow('Hand Gesture Control - STABLE MODE', processed_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        if is_dragging: 
            controller.end_drag()
        running = False
        cap.release()
        cv2.destroyAllWindows()
        mouse_thread.join(timeout=1.0)

print("Program ended successfully")