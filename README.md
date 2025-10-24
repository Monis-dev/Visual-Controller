# Visual-Controller
```markdown
# 🖐️ Advanced Hand Gesture Computer Control System

A **real-time, vision-based system** that enables full computer control using hand gestures. This project transforms your webcam into a powerful input device — allowing you to move the cursor, click, drag, scroll, and even control PowerPoint presentations **without touching your mouse or keyboard**.

---

## 🚀 Overview

This project uses **MediaPipe** for gesture recognition, **OpenCV** for video processing, and **PyAutoGUI** for system interaction — all orchestrated through a **multi-threaded architecture** to ensure maximum performance, responsiveness, and stability.

It supports:
- **Right hand** for cursor and mouse control  
- **Left hand** for mode switching (e.g., entering Presentation Mode)

---

## 🧠 Core Features

### ✋ Right Hand Controls (Standard Mode)
| Gesture | Action |
|----------|--------|
| **POINTING (Index Finger)** | Move the cursor |
| **PINCH (Thumb + Index)** | Drag & Drop |
| **OPEN Hand** | Left Click |
| **CLOSE (Fist)** | Right Click (hold briefly) |
| **Double CLOSE (Double Fist)** | Double Click |
| **SCROLL (Index + Middle Up)** | Scroll vertically by moving hand up/down |
| **COLAPS (Custom)** | Close active app (`Alt + F4`) |

---

### 🤝 Dual-Hand Controls (Presentation Mode)
| Gesture | Action |
|----------|--------|
| **Left Hand PPT Gesture** | Enter Presentation Mode |
| **Left Hand CLOSE (Fist)** | Exit Presentation Mode |
| **Right Hand SCROLL + Swipe** | Navigate Slides (← / →) |
| **Right Hand OPEN** | Start Slideshow (`F5`) |
| **Right Hand CLOSE (Fist)** | End Slideshow (`Esc`) |

---

## ⚙️ Stability & Smoothing Features

- **Multi-threaded architecture** — 4 concurrent threads:
  - Camera Thread  
  - Gesture Recognition Thread  
  - Main/UI Thread  
  - Mouse Controller Thread  

- **Advanced Filtering Pipeline:**
  - Moving Average Filter  
  - Kalman Filter (predictive)  
  - Exponential Smoothing (lerp)  
  - Adaptive Smoothing based on velocity  
  - Deadzone for micro tremor rejection  

- **Manual Failsafe:**  
  Move cursor to any corner to pause gesture control.  
  Resume with an OPEN hand gesture.

---

## 🧩 System Architecture

### 🔄 Workflow Diagram (Conceptual)
```
Camera → Frame Queue → Gesture Recognition → Results Queue
↓
Main/UI Thread
↓
Mouse Queue → Mouse Controller
```

### 🧵 Thread Responsibilities
- **Camera Thread:** Captures frames continuously and feeds them into a queue.  
- **Gesture Recognition Thread:** Processes frames using MediaPipe and identifies gestures.  
- **Main/UI Thread:** Handles logic, state transitions, and rendering UI.  
- **Mouse Controller Thread:** Moves cursor independently for ultra-smooth motion.

---

## 📁 Code Structure

```
📦 Advanced-Hand-Gesture-Control
│
├── main.py                  # Main application logic and threading
├── gesture_recognizer.py    # Handles MediaPipe-based gesture detection
├── computer_controller.py   # Executes mouse & keyboard commands
├── smoothing_utils.py       # Contains all smoothing and filtering algorithms
├── config.py                # Centralized settings and tunable parameters
├── ui_utils.py              # Handles on-screen visualization (FPS, gesture status)
└── requirements.txt         # Python dependencies
```

---

## 🧮 Key Components

### **`gesture_recognizer.py` – The Eyes 👁️**
- Detects hand landmarks using **MediaPipe**.  
- Maps geometric positions to gesture names (e.g., `"PINCH"`, `"OPEN"`).  
- Uses a **gesture buffer** to stabilize recognition (prevents flickering).  

### **`computer_controller.py` – The Hands 🖱️**
- Uses **PyAutoGUI** and `ctypes` for optimized system control.  
- Handles clicking, dragging, scrolling, and PPT navigation.  
- Implements a **custom failsafe** to prevent unwanted actions.  

### **`smoothing_utils.py` – The Stabilizer 🎯**
- Provides functions for:
  - Moving Average  
  - Kalman Filter  
  - Exponential Smoothing  
  - Adaptive Velocity-based filtering  
  - Deadzone correction  

### **`config.py` – Settings ⚙️**
- Adjustable constants (e.g., smoothing factors, sensitivity, cooldowns).  
- Easy tweaking without modifying the logic.  

### **`ui_utils.py` – The Display 💻**
- Draws gesture indicators, FPS, and debug info using OpenCV.  
- Keeps the main loop clean and minimal.  

---

## 🧰 Technologies Used

| Library | Purpose |
|----------|----------|
| **Python 3** | Core programming language |
| **OpenCV (cv2)** | Video capture and rendering |
| **MediaPipe** | Real-time hand tracking |
| **PyAutoGUI** | Mouse & keyboard control |
| **NumPy** | Numerical computation |
| **threading / queue** | Concurrency and data passing |

---

## ⚡ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/Advanced-Hand-Gesture-Control.git
   cd Advanced-Hand-Gesture-Control
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the project:**
   ```bash
   python main.py
   ```

4. **Usage:**
   - Ensure your webcam is enabled.  
   - Raise your hand and start controlling your computer hands-free!  

---

## 🧑‍💻 Developer Notes

- Built with modularity in mind — each subsystem can be tested independently.  
- Thread-safe queues ensure no frame loss or blocking.  
- All gestures are configurable and extendable via `gesture_recognizer.py`.  
- Ideal for accessibility, touchless control, or smart presentation tools.  

---

## 🧾 License

This project is open-source under the **MIT License**.  
Feel free to modify, enhance, or integrate it into your own systems.

---

## 💡 Future Enhancements

- Voice + Gesture hybrid controls  
- Machine-learning–based custom gesture training  
- Multi-camera support  
- Gesture-based typing and window management  

---

🎥 **Experience touchless computing — powered by vision, precision, and code.**
```
