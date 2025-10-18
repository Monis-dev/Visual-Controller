import cv2 
import time
import threading
import queue
import numpy as np
from gesture_recognizer import GestureRecognizer
from computer_controller import ComputerController

print("Attempting to connect to camera")
cap = cv2.VideoCapture(1)

recognizer = GestureRecognizer()
controller = ComputerController()

# Use a standard webcam resolution for better performance and compatibility
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# --- STATE VARIABLES ---
last_gesture = "IDLE"
prev_frame_time = 0
smoothing_factor = 0.4
prev_x, prev_y = 0, 0
is_pointer_locked = False # State for locking the pointer

last_click_time = 0
CLICK_COOLDOWN = 0.3

# For Double Right-Click
last_close_gesture_time = 0
close_gesture_count = 0
DOUBLE_CLICK_WINDOW = 0.6
SINGLE_CLICK_DELAY = 0.7

is_dragging = False
FRAME_REDUCTION = 0.2
running = True

mouse_queue = queue.Queue(maxsize=2)

def mouse_controller_thread():
    while running:
        try:
            x, y = mouse_queue.get(timeout=0.05)
            if not is_dragging and not is_pointer_locked:
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
    print("\nControls:")
    print("  👆 POINTING → Move cursor")
    print("  🤏 PINCH → Drag")
    print("  ✋ OPEN HAND → Left Click")
    print("  ✊ FIST (once) → Right Click")
    print("  ✊ FIST (twice quickly) → Double Right Click")
    print("\nINFO: Move your physical mouse to any screen corner to PAUSE.")
    print("      Show OPEN HAND to RESUME.\n")
    
    try:
        while True:
            success, frame = cap.read()
            if not success: continue

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

            current_gesture, confidence = recognizer.get_gesture()
            current_time = time.time()


            x_min_bound = int(FRAME_REDUCTION * frame_width)
            y_min_bound = int(FRAME_REDUCTION * frame_height)
            x_max_bound = int(frame_width - (FRAME_REDUCTION * frame_width))
            y_max_bound = int(frame_height - (FRAME_REDUCTION * frame_height))

            if not is_pointer_locked:
                active_area_color = (255, 255, 0)
                if landmarks:
                    pointer_coords, _, _ = recognizer.get_pointer_coordinates(processed_frame.shape)
                    if pointer_coords:
                        raw_x, raw_y = pointer_coords
                        screen_x = np.interp(raw_x, (x_min_bound, x_max_bound), (0, controller.screen_width))
                        screen_y = np.interp(raw_y, (y_min_bound, y_max_bound), (0, controller.screen_height))
                        
                        current_x = prev_x + (screen_x - prev_x) * smoothing_factor
                        current_y = prev_y + (screen_y - prev_y) * smoothing_factor
                        
                        # Send to mouse thread (removed the *1.5 scaling, which is redundant with FRAME_REDUCTION)
                        if not is_dragging:
                            try: mouse_queue.put_nowait((current_x, current_y))
                            except queue.Full: pass
                        else: 
                            controller.point_movement(int(current_x), int(current_y))
                        
                        prev_x, prev_y = current_x, current_y
                        
                        pointer_color = (0, 0, 255) if is_dragging else (0, 255, 0)
                        cv2.circle(processed_frame, pointer_coords, 10, pointer_color, -1)
                
                if current_gesture == "PINCH" and last_gesture != "PINCH":
                    if not is_dragging:
                        controller.start_drag()
                        is_dragging = True
                        print("Drag Started")

                elif current_gesture != "PINCH" and is_dragging:
                    controller.end_drag()
                    is_dragging = False
                    print("Drag Ended")

                if not is_dragging and confidence > 0.7:

                    if current_gesture == "OPEN" and last_gesture != "OPEN":
                        if (current_time - last_click_time) > CLICK_COOLDOWN:
                            controller.left_click()
                            last_click_time = current_time
                            print("Left Click")
                    elif current_gesture == "CLOSE" and last_gesture != "CLOSE":
                        time_since_last_close = current_time - last_close_gesture_time

                        if time_since_last_close < DOUBLE_CLICK_WINDOW and close_gesture_count == 1:
                            controller.double_left_click()
                            last_click_time = current_time
                            close_gesture_count = 0
                            last_close_gesture_time = 0
                            print("Double left click")
                        else:
                            close_gesture_count = 1
                            last_close_gesture_time = current_time

                if close_gesture_count == 1:
                    time_since_last_close = current_time - last_close_gesture_time
                    if time_since_last_close > SINGLE_CLICK_DELAY:
                        controller.right_click()
                        last_click_time = current_time
                        close_gesture_count = 0 
                        last_close_gesture_time = 0
                        print("Right click")                                          


            
            else: # --- POINTER IS LOCKED ---
                active_area_color = (0, 0, 255)
                cv2.putText(processed_frame, "POINTER LOCKED", (frame_width//2 - 150, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                cv2.putText(processed_frame, "Show OPEN HAND to resume", (frame_width//2 - 200, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

                # --- UNLOCK AND RECALIBRATE LOGIC ---
                if current_gesture == "OPEN" and confidence > 0.8:
                    is_pointer_locked = False
                    # **THE FIX FOR THE INFINITE LOOP**
                    # Move cursor to last known hand position to break the corner condition
                    controller.point_movement(int(prev_x), int(prev_y))
                    last_click_time = time.time()
                    print("INFO: Pointer recalibrated and resumed by user.")

            last_gesture = current_gesture

            # Visual Feedback
            cv2.rectangle(processed_frame, (x_min_bound, y_min_bound), (x_max_bound, y_max_bound), active_area_color, 2)
            gesture_text = f"Gesture: {current_gesture}"
            if is_dragging: gesture_text += " (DRAGGING)"
            if is_pointer_locked: gesture_text = "LOCKED"
            cv2.putText(processed_frame, gesture_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(processed_frame, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow('Hand Gesture Control', processed_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        if is_dragging: controller.end_drag()
        running = False
        cap.release()
        cv2.destroyAllWindows()
        mouse_thread.join(timeout=1.0)

print("Program ended successfully")