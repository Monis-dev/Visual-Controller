import cv2 

from gesture_recognizer import GestureRecognizer

from computer_controller import ComputerController


print("Attempting to conect to camera")
cap = cv2.VideoCapture(1)

recognizer = GestureRecognizer()
controller = ComputerController()
last_gesture = "UNKNOWN"

if not cap.isOpened():
    print("Error: Could not connect to the camera")

else :
    print("Success! Camera stream is open. Reading frames")
    while True:
        success, frame = cap.read()

        if not success:
            print("Ignoring empty camera frame")
            continue

        processed_frame, landmarks = recognizer.find_hand_landmarks(frame)

        if landmarks:
            pointer_coords = recognizer.get_pointer_coordinates(processed_frame.shape)
            controller.point_movement(pointer_coords[0], pointer_coords[1] )
            # if pointer_coords:
            #     print(f"Pointer at: {pointer_coords}")  

        current_gesture = recognizer.get_gesture()

        if current_gesture != last_gesture:
            if current_gesture == "OPEN":
                controller.left_click()
            elif current_gesture == "CLOSE":
                controller.right_click()
            last_gesture = current_gesture    

        cv2.imshow("Visual Controller", processed_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()

#.\venv\Scripts\activate