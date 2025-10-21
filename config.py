# 1. EXPONENTIAL SMOOTHING (Primary smoothing)
smoothing_factor = 0.3  # Lower = smoother but slower (0.1-0.5)

# 2. MOVING AVERAGE FILTER (Secondary smoothing)
position_buffer_size = 5  # Average of last N positions

# 3. KALMAN-LIKE FILTERING (Advanced smoothing)
use_kalman_filter = True
kalman_process_variance = 0.01  # How much we trust hand movement
kalman_measurement_variance = 0.1  # How much we trust sensor

# 4. DEADZONE (Ignore tiny movements)
DEADZONE_PIXELS = 3  # Ignore movements smaller than this

# 5. VELOCITY LIMITING (Prevent sudden jumps)
MAX_VELOCITY = 80  # Maximum pixels per frame (Note: This function was missing its implementation, I've added it in smoothing_utils.py)

# 6. ADAPTIVE SMOOTHING (Smooth more when hand is still)
use_adaptive_smoothing = True
velocity_threshold_for_adaptive = 20  # pixels/frame

# --- Other Settings ---
CLICK_COOLDOWN = 0.3
DOUBLE_CLICK_WINDOW = 0.6
SINGLE_CLICK_DELAY = 0.7

SCROLL_SENSITIVITY = 550
SCROLL_DEADZONE = 0.01

FRAME_REDUCTION = 0.2

