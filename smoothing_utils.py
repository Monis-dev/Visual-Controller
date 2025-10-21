# smoothing_utils.py
import numpy as np

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
    distance = np.sqrt(dx**2 + dy**2) # Corrected this line

    if distance > max_velocity:
        # Scale down to max velocity
        if distance > 0:
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