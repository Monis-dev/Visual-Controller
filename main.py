import cv2 

from gesture_recognizer import GestureRecognizer


print("Attempting to conect to camera")
cap = cv2.VideoCapture(1)

recognizer = GestureRecognizer()

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

            if pointer_coords:
                print(f"Pointer at: {pointer_coords}")    
        cv2.imshow("Visual Controller", processed_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()