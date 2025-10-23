import cv2 
import time
import threading
import queue
import numpy as np
from collections import deque

# Import our new utility modules
import smoothing_utils as su
import ui_utils as ui
import config  # We'll also move settings to config.py for cleanliness

# Import your classes
from gesture_recognizer import GestureRecognizer
from computer_controller import ComputerController

print("Initializing...")
WINDOW_NAME = 'Hand Gesture Control - STABLE MODE'

# --- THREAD-SAFE QUEUES ---
frame_queue = queue.Queue(maxsize=2)  # Holds raw frames from the camera
results_queue = queue.Queue(maxsize=2) # Holds processed data from the gesture recognizer

# --- INITIALIZATION ---
recognizer = GestureRecognizer()
controller = ComputerController()
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Error: Could not connect to the camera. Exiting.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# --- STATE & SETTINGS ---
# Buffers for smoothing
position_buffer_x = deque(maxlen=config.position_buffer_size)
position_buffer_y = deque(maxlen=config.position_buffer_size)

# Kalman filter state
kalman_x, kalman_y = 0, 0
kalman_p_x, kalman_p_y = 1, 1

# Other state variables
is_pointer_locked = False
is_dragging = False
is_scrolling = False
is_swiping = False
swipe_start_x = 0
swipe_action_taken = False
prev_x, prev_y = 0, 0
last_gesture = "IDLE"

# Timing and gesture counts
last_click_time = 0
last_close_gesture_time = 0
close_gesture_count = 0

running = True

prev_frame_time = 0
latest_results = None
velocity = 0

mouse_queue = queue.Queue(maxsize=2)

# PPT checker
is_ppt_mode = False

def camera_thread_func():
    """Grabs frames from the camera and puts them in a queue."""
    while running:
        success, frame = cap.read()
        if not success:
            time.sleep(0.1)
            continue
        try:
            # Flips the frame horizontally for a more intuitive mirror-like effect
            frame_queue.put(frame, block=False)
        except queue.Full:
            # If the processing is slow, we just skip frames
            pass
    print("Camera thread stopped.")

def gesture_thread_func():
    """Processes frames for gesture recognition."""
    while running:
        try:
            frame = frame_queue.get(timeout=0.1)
            # Process the frame to find hand landmarks and gesture
            processed_frame, landmarks, hand_type = recognizer.find_hand_landmarks(frame)
            current_gesture, confidence = recognizer.get_gesture()
            
            result = {
                "frame": processed_frame,
                "landmarks": landmarks,
                "gesture": current_gesture,
                "confidence": confidence,
                "hand_type": hand_type  # <<< CHANGED: Add hand_type to the results dictionary
            }
            
            results_queue.put(result, block=False)
            
        except queue.Empty:
            continue
        except queue.Full:
            pass
    print("Gesture thread stopped.")

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
print(f"  • Exponential smoothing: {config.smoothing_factor}")
print(f"  • Moving average: {config.position_buffer_size} frames")
print(f"  • Kalman filter: {'ON' if config.use_kalman_filter else 'OFF'}")
print(f"  • Deadzone: {config.DEADZONE_PIXELS}px")
print(f"  • Velocity limit: {config.MAX_VELOCITY}px/frame")
print(f"  • Adaptive smoothing: {'ON' if config.use_adaptive_smoothing else 'OFF'}\n")

cam_thread = threading.Thread(target=camera_thread_func, daemon=True)
rec_thread = threading.Thread(target=gesture_thread_func, daemon=True)
mouse_thread = threading.Thread(target=mouse_controller_thread, daemon=True)

cam_thread.start()
rec_thread.start()
mouse_thread.start()


try:
    while running:
        # Get the latest processed results from the gesture thread
        try:
            results = results_queue.get_nowait()
            latest_results = results
            processed_frame = results['frame']
        except queue.Empty:
            # If no new results, use the last frame to keep UI responsive
            if latest_results:
                processed_frame = latest_results['frame']
            else:
                # Show a loading screen until the first frame is processed
                loading_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(loading_frame, "Waiting for camera...", (450, 360), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.imshow(WINDOW_NAME, loading_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
                continue
        # --- UNPACK RESULTS & CALCULATE TIMINGS ---
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - prev_frame_time) if prev_frame_time > 0 else 0
        prev_frame_time = new_frame_time
        current_time = time.time()
        landmarks = latest_results['landmarks']
        current_gesture = latest_results['gesture']
        confidence = latest_results['confidence']
        # <<< CHANGED: Get hand_type safely from the results dictionary
        hand_type = latest_results.get('hand_type', None) 
        
        frame_height, frame_width, _ = processed_frame.shape
        x_min_bound = int(config.FRAME_REDUCTION * frame_width)
        y_min_bound = int(config.FRAME_REDUCTION * frame_height)
        x_max_bound = int(frame_width - (config.FRAME_REDUCTION * frame_width))
        y_max_bound = int(frame_height - (config.FRAME_REDUCTION * frame_height))
        
        # --- GESTURE LOGIC ---
        if not is_pointer_locked and controller.check_for_manual_failsafe():
            is_pointer_locked = True
            if is_dragging: controller.end_drag(); is_dragging = False
            if is_scrolling: is_scrolling = False
            print("⏸ PAUSED")

        if not is_pointer_locked:
            # --- RIGHT HAND LOGIC ---
            if hand_type == "Right":
                # --- PPT MODE ACTIONS (RIGHT HAND) ---
                if is_ppt_mode:
                    if landmarks and current_gesture == "SCROLL":
                        if not is_swiping:
                            is_swiping = True
                            swipe_start_x = landmarks.landmark[9].x 
                            swipe_action_taken = False
                            print("↔️  Swipe gesture initiated")
                        elif not swipe_action_taken:
                            current_x = landmarks.landmark[9].x
                            delta_x = current_x - swipe_start_x
                            if abs(delta_x) > config.SWIPE_THRESHOLD:
                                if delta_x > 0:
                                    controller.left_slide()
                                    print("    ➡️  Swiped Right (Action: Left Arrow)")
                                else:
                                    controller.right_slide()
                                    print("    ⬅️  Swiped Left (Action: Right Arrow)")
                                swipe_action_taken = True 
                    elif is_swiping and current_gesture != "SCROLL":
                        is_swiping = False
                        swipe_start_x = 0
                        swipe_action_taken = False
                        print("↔️  Swipe gesture ended")

                    if current_gesture == "OPEN" and last_gesture != "OPEN":
                        controller.start_slide()
                        print("PPT Started")
                    elif current_gesture == "CLOSE" and last_gesture != "CLOSE":
                        controller.close_slide()
                        print("PPT Ended")
                
                # --- NORMAL OS MODE ACTIONS (RIGHT HAND) ---
                else: 
                    # SCROLL HANDLING
                    if landmarks and current_gesture == "SCROLL":
                        if not is_scrolling:
                            is_scrolling = True
                            scroll_start_y = landmarks.landmark[12].y
                            last_scroll_time = current_time
                            print("📜 Scroll started")
                        else:
                            current_scroll_y = landmarks.landmark[12].y
                            delta_y = scroll_start_y - current_scroll_y
                            if abs(delta_y) > config.SCROLL_DEADZONE and (current_time - last_scroll_time) > 0.05:
                                scroll_amount = int(delta_y * config.SCROLL_SENSITIVITY)
                                if scroll_amount != 0: 
                                    controller.scroll(scroll_amount)
                                    last_scroll_time = current_time
                                scroll_start_y = current_scroll_y    
                    elif is_scrolling:
                        is_scrolling = False
                        scroll_start_y = 0
                        print("📜 Scroll ended")

                    # CURSOR MOVEMENT
                    if not is_scrolling and landmarks:
                        pointer_coords, _, _ = recognizer.get_pointer_coordinates(processed_frame.shape)
                        if pointer_coords:
                            raw_x, raw_y = pointer_coords
                            screen_x = np.interp(raw_x, (x_min_bound, x_max_bound), (0, controller.screen_width))
                            screen_y = np.interp(raw_y, (y_min_bound, y_max_bound), (0, controller.screen_height))
                            screen_x = su.moving_average_filter(position_buffer_x, screen_x)
                            screen_y = su.moving_average_filter(position_buffer_y, screen_y)
                            if config.use_kalman_filter:
                                kalman_x, kalman_p_x = su.kalman_filter(kalman_x, kalman_p_x, screen_x, config.kalman_measurement_variance, config.kalman_process_variance)
                                kalman_y, kalman_p_y = su.kalman_filter(kalman_y, kalman_p_y, screen_y, config.kalman_measurement_variance, config.kalman_process_variance)
                                screen_x, screen_y = kalman_x, kalman_y
                            velocity = np.sqrt((screen_x - prev_x)**2 + (screen_y - prev_y)**2)
                            current_smoothing = su.adaptive_smoothing_factor(velocity, config.smoothing_factor, config.velocity_threshold_for_adaptive) if config.use_adaptive_smoothing else config.smoothing_factor
                            current_x = prev_x + (screen_x - prev_x) * current_smoothing
                            current_y = prev_y + (screen_y - prev_y) * current_smoothing
                            current_x, current_y = su.apply_deadzone(current_x, current_y, prev_x, prev_y, config.DEADZONE_PIXELS)
                            if not is_dragging:
                                try: mouse_queue.put_nowait((current_x, current_y))
                                except queue.Full: pass
                            else:
                                controller.point_movement(int(current_x), int(current_y))
                            prev_x, prev_y = current_x, current_y

                    # DRAG & CLICK HANDLING
                    if not is_scrolling:
                        if current_gesture == "PINCH" and not is_dragging:
                            controller.start_drag(); is_dragging = True; print("🖱 Drag started")
                        elif current_gesture != "PINCH" and is_dragging:
                            controller.end_drag(); is_dragging = False; print("🖱 Drag ended")
                        if not is_dragging and confidence > 0.7:
                            if current_gesture == "OPEN" and last_gesture != "OPEN" and (current_time - last_click_time) > config.CLICK_COOLDOWN:
                                controller.left_click(); last_click_time = current_time; print("🖱 Left Click")
                            elif current_gesture == "CLOSE" and last_gesture != "CLOSE":
                                if (current_time - last_close_gesture_time) < config.DOUBLE_CLICK_WINDOW and close_gesture_count == 1:
                                    controller.double_left_click(); last_click_time = current_time; close_gesture_count = 0; print("🖱🖱 Double Left Click")
                                else:
                                    close_gesture_count = 1; last_close_gesture_time = current_time
                            elif current_gesture == "COLAPS" and last_gesture != "COLAPS":
                                controller.colaps(); print("Closing folder")
                    if close_gesture_count == 1 and (current_time - last_close_gesture_time) > config.SINGLE_CLICK_DELAY:
                        controller.right_click(); last_click_time = current_time; close_gesture_count = 0; print("🖱 Right Click")

            # --- LEFT HAND LOGIC (PPT MODE TOGGLE) ---
            elif hand_type == "Left":
                if current_gesture == "PPT" and not is_ppt_mode:
                    is_ppt_mode = True
                    print("✅ PPT Mode ACTIVATED")
                # <<< CHANGED: Check for "CLOSE" instead of "DEACTIVATE"
                elif current_gesture == "CLOSE" and is_ppt_mode:
                    is_ppt_mode = False
                    print("❌ PPT Mode DEACTIVATED")

        else: # LOCKED STATE LOGIC
            if current_gesture == "OPEN" and confidence > 0.8:
                is_pointer_locked = False
                print("▶ RESUMED")

        last_gesture = current_gesture
        # --- DRAWING ---
        ui_state = {
            'fps': fps, 'current_gesture': current_gesture, 'confidence': confidence,
            'is_dragging': is_dragging, 'is_scrolling': is_scrolling, 'is_pointer_locked': is_pointer_locked,
            'x_min_bound': x_min_bound, 'y_min_bound': y_min_bound,
            'x_max_bound': x_max_bound, 'y_max_bound': y_max_bound,
            'active_area_color': (0, 0, 255) if is_pointer_locked else (255, 255, 0),
            'close_gesture_count': close_gesture_count, 'last_close_gesture_time': last_close_gesture_time,
            'pointer_coords': recognizer.get_pointer_coordinates(processed_frame.shape)[0] if landmarks else None,
            'velocity': velocity,
            'is_ppt_mode': is_ppt_mode # Pass PPT mode state to UI
        }
        ui.draw_ui_elements(processed_frame, ui_state)
        cv2.imshow(WINDOW_NAME, processed_frame)
        
        # --- EXIT CONDITION ---
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            running = False
            break
finally:
    print("Cleaning up resources...")
    running = False
    print("Waiting for threads to join...")
    cam_thread.join(timeout=1.0)
    rec_thread.join(timeout=1.0)
    mouse_thread.join(timeout=1.0)
    controller.failsafe_cleanup()
    if cap.isOpened():
        cap.release()
        print("Camera released.")
    cv2.destroyAllWindows()
    print("Windows destroyed.")
print("Program ended successfully")