import pyautogui

class ComputerController:
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()

    def left_click(self):
        pyautogui.click(button="left")
        print("Actions: Left CLick")

    def right_click(self):
        pyautogui.click(button="right")
        print("Actions: Right Click");        

    def point_movement(self, x_coord, y_coord):
        pyautogui.moveTo(x_coord, y_coord)
        # print(f"Pointer location: {x_coord, y_coord}")