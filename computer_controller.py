import pyautogui
import pygetwindow
import platform
import time

class ComputerController:
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        
        # CRITICAL: Disable PyAutoGUI's automatic failsafe
        pyautogui.FAILSAFE = False  # This prevents the corner crash
        pyautogui.PAUSE = 0  # Remove default delay for speed
        
        # Platform-specific optimizations
        self.use_ctypes = False
        if platform.system() == "Windows":
            try:
                import ctypes
                self.user32 = ctypes.windll.user32
                self.use_ctypes = True
                print("Using ctypes for faster mouse control on Windows")
            except:
                print("ctypes not available, using pyautogui")
        
        # For drag functionality
        self.is_dragging = False
        
        # Manual failsafe settings
        self.corner_threshold = 50  # pixels from edge
        self.last_failsafe_check = 0
        self.failsafe_check_interval = 0.1  # Check every 100ms
        
        print(f"✓ Screen resolution: {self.screen_width}x{self.screen_height}")
    
    def point_movement(self, x, y):
        """Optimized mouse movement"""
        # Clamp coordinates to screen bounds
        x = max(0, min(int(x), self.screen_width - 1))
        y = max(0, min(int(y), self.screen_height - 1))
        
        try:
            if self.use_ctypes:
                # Much faster on Windows using ctypes
                self.user32.SetCursorPos(x, y)
            else:
                # Faster pyautogui call
                pyautogui.moveTo(x, y, _pause=False)
        except Exception as e:
            print(f"Mouse movement error: {e}")
    
    def left_click(self):
        """Perform left click"""
        try:
            pyautogui.click(_pause=False)
        except Exception as e:
            print(f"Left click error: {e}")
    
    def right_click(self):
        """Perform right click"""
        try:
            pyautogui.rightClick(_pause=False)
        except Exception as e:
            print(f"Right click error: {e}")
    
    def double_right_click(self):
        """Perform double right click"""
        try:
            pyautogui.rightClick(_pause=False)
            pyautogui.rightClick(_pause=False)
        except Exception as e:
            print(f"Double right click error: {e}")
    
    def double_left_click(self):
        """Perform double left click"""
        try:
            pyautogui.doubleClick(_pause=False)
        except Exception as e:
            print(f"Double left click error: {e}")
    
    def scroll(self, amount):
        """
        Scroll the mouse wheel.
        Positive amount = scroll up
        Negative amount = scroll down
        """
        try:
            pyautogui.scroll(amount, _pause=False)
        except Exception as e:
            print(f"Scroll error: {e}")
    
    def right_slide(self):
        try:
            pyautogui.press("right", _pause=False)
        except Exception as e:
            print(f"Error performing right button {e}")    

    def left_slide(self):
        try:
            pyautogui.press("left", _pause=False)
        except Exception as e:
            print(f"Error performing right button {e}")    

    def start_slide(self):
        try:
            pyautogui.press("f5", _pause=False)
        except Exception as e:
            print(f"Error performing right button {e}")    

    def close_slide(self):
        try:
            pyautogui.press("escape", _pause=False)
        except Exception as e:
            print(f"Error performing right button {e}")    


    def colaps(self):
        """Closing program"""
        try:
            pyautogui.hotkey('alt', 'f4', _pause=False)
        except Exception as e:
            print(f"Error closing program {e}")    

    def start_drag(self):
        """Start dragging (mouse down)"""
        try:
            if not self.is_dragging:
                pyautogui.mouseDown(_pause=False)
                self.is_dragging = True
        except Exception as e:
            print(f"Start drag error: {e}")
    
    def end_drag(self):
        """End dragging (mouse up)"""
        try:
            if self.is_dragging:
                pyautogui.mouseUp(_pause=False)
                self.is_dragging = False
        except Exception as e:
            print(f"End drag error: {e}")
    
    def check_for_manual_failsafe(self):
        """
        Manual failsafe: Check if cursor is in any screen corner.
        This replaces PyAutoGUI's automatic failsafe.
        Returns True if cursor is in a corner.
        """
        
        # Throttle checks for performance
        current_time = time.time()
        if current_time - self.last_failsafe_check < self.failsafe_check_interval:
            return False
        
        self.last_failsafe_check = current_time
        
        try:
            # Get current mouse position
            x, y = pyautogui.position()
            
            # Check all four corners
            in_top_left = (x < self.corner_threshold and y < self.corner_threshold)
            in_top_right = (x > self.screen_width - self.corner_threshold and y < self.corner_threshold)
            in_bottom_left = (x < self.corner_threshold and y > self.screen_height - self.corner_threshold)
            in_bottom_right = (x > self.screen_width - self.corner_threshold and 
                              y > self.screen_height - self.corner_threshold)
            
            return in_top_left or in_top_right or in_bottom_left or in_bottom_right
            
        except Exception as e:
            print(f"Failsafe check error: {e}")
            return False
    
    def get_cursor_position(self):
        """Get current cursor position"""
        try:
            return pyautogui.position()
        except:
            return (0, 0)
        

    def failsafe_cleanup(self):
        """Release all the mouse button and common modifier keys"""
        print("Running failsafe cleanup: Releasing all keys and buttons.")

        if self.is_dragging:
            self.end_drag()

        for button in ['left', 'right', 'middle']:
            try:
                pyautogui.mouseUp(button=button, _pause=False)
            except Exception:
                pass 
            for key in ['ctrl', 'shift', 'alt', 'win']:
                try:
                    pyautogui.keyUp(key, _pause=False)    
                except Exception:
                    pass    
    
    def check_ppt_mode(self):
        window_type = ".ppt"  
        try: 
            active_window = pygetwindow.getActiveWindow()
            window_title = active_window.title 
            if window_title == '.ppt':
                print("PPT detected")
                return True
        except:
            pass

        