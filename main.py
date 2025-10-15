import cv2 
import time
from gesture_recognizer import GestureRecognizer
from computer_controller import ComputerController
from utils import Utils
import threading
import queue


print("Attempting to conect to camera")
cap = cv2.VideoCapture(1)

recognizer = GestureRecognizer()
controller = ComputerController()
utils = Utils()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, controller.screen_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, controller.screen_height)
cap.set(cv2.CAP_PROP_FPS, 60)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)


last_gesture = "UNKNOWN"
current_gesture = "UNKNOWN"
prev_frame_time = 0
new_frame_time = 0
# cursor_x, cursor_y = 0, 0
smoothing_factor = 2
prev_x, prev_y = 0, 0
frame_count = 0 

mouse_queue = queue.Queue(maxsize=2)
running = True

def mouse_controller_thread():
    """Dedicated thread for non-blocking mouse movement."""
    while running: 
        try:
            # --- FIX 1: Get from the queue, don't call the function again! ---
            x, y = mouse_queue.get(timeout=0.05)
            controller.point_movement(int(x), int(y))
        except queue.Empty:
            # This is expected if the main thread is slower, just continue waiting
            continue
        except Exception as e:
            print(f"Error in mouse thread: {e}")
            break
mouse_thread = threading.Thread(target=mouse_controller_thread, daemon=True)
mouse_thread.start()


if not cap.isOpened():
    print("Error: Could not connect to the camera")
else :
    print("Success! Camera stream is open. Reading frames")
    try:
        while True:
            success, frame = cap.read()
            frame_count += 1

            if not success:
                print("Ignoring empty camera frame")
                continue
            
            new_frame_time = time.time()
            delta_time = new_frame_time - prev_frame_time
            fps = 1 / delta_time if delta_time > 0 else 0
            prev_frame_time = new_frame_time     
            fps_text = f"FPS: {int(fps)}"

            processed_frame, landmarks = recognizer.find_hand_landmarks(frame)

            if landmarks:
                pointer_coords, frame_width, frame_height = recognizer.get_pointer_coordinates(processed_frame.shape)
                if pointer_coords:
                    screen_x = (pointer_coords[0] / frame_width) * controller.screen_width
                    screen_y = (pointer_coords[1] / frame_height) * controller.screen_height
                    # cursor_x = utils.lerp(cursor_x, screen_x, 0.3)
                    # cursor_y = utils.lerp(cursor_y, cursor_y, 0.3)

                    current_x = prev_x + (screen_x - prev_x) / smoothing_factor
                    current_y = prev_y + (screen_y - prev_y) / smoothing_factor
                    
                    try:
                        while not mouse_queue.empty():
                            try:
                                mouse_queue.get_nowait()
                            except:
                                break
                        mouse_queue.put_nowait((current_x, current_y))
                        
                    except queue.Full:
                        pass  
                    prev_x = current_x
                    prev_y = current_y      
                    
                # if pointer_coords:
                #     print(f"Pointer at: {pointer_coords}")  

            if frame_count % 2 == 0:  # Only check for gestures every 3 frames
                current_gesture = recognizer.get_gesture()

            if current_gesture != last_gesture:
                if current_gesture == "OPEN":
                    controller.left_click()
                elif current_gesture == "CLOSE":
                    controller.right_click()
                last_gesture = current_gesture 

            cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.imshow('Frame with FPS', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        running = False        
        mouse_thread.join(timeout=1.0)    
        cap.release()
        cv2.destroyAllWindows()
#.\venv\Scripts\activate