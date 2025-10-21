            current_y = prev_y + (screen_y - prev_y) * current_smoothing
                    current_x, current_y = su.apply_deadzone(current_x, current_y, prev_x, prev_y, config.DEADZONE_PIXELS)
          