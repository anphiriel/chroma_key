## chroma_key: Chroma Key Compositor Demo App

This repository showcases a demonstration of greenscreen (chroma‐key) compositing using Python, OpenCV, and Tkinter. 

---

## Overview

1. **`chroma_key_core.py`**  
   Contains the **core chroma‐key and compositing logic** (greenscreen removal).  
   - Implements the primary function `perform_chroma_key(...)` to blend a foreground (greenscreen) video with a background (image or second video).  
   - Includes an **optional advanced feature** `apply_gamma_correction(...)` for demonstrating color adjustment expertise.  
   - Strictly computational routines—no GUI code here.

2. **`chroma_key_gui.py`**  
   Provides a **Tkinter‐based interface** for loading videos, picking the key color, adjusting various parameters (tolerance, softness, brightness, contrast), and exporting the final composited video.  

---

## Key Features

1. **Greenscreen Removal**  
   - Dynamically pick a target color (e.g. green) to remove from the foreground video.  
   - Control the tolerance range and softness of edges (feathering) to achieve seamless compositing.

2. **Foreground & Background Adjustments**  
   - Brightness and contrast sliders for both the foreground and the background.  
   - Fine‐tune overall look, ensuring a cohesive final composite.

3. **Preview & Export**  
   - **Play** the fully composited video in real-time (or approx).  
   - **Export** final video.

---

## Installation

1. **Clone or Download** this repository:
```bash
git clone https://github.com/YourUsername/chroma_key.git
cd chroma_key
```

2. **Dependencies**: 
	- Python >= 3.7
	- OpenCV (opencv-python)
	- NumPy
	- Tkinter (often included with Python on Windows/macOS; on some Linux distros, install python3-tk)

Install via pip:
```bash
pip install opencv-python numpy
```

3. **Run the App**: 
```bash
python chroma_key_gui.py
```

## Usage

1. Load Foreground Video
Click “Load Foreground Video” and select a .mp4 file, ideally with a greenscreen or solid background.

3.	Pick Chroma Key Color
Optionally click “Pick Chroma Key Color” to open a window where you drag a bounding box around the background color to remove. The default is set to green (0, 255, 0).

5.	Load Background
Click “Load Background” and choose either Image or Video as the source.
If video, frames are preloaded for short background clips.
If image, it remains static throughout the composite.

7.	Adjust Sliders
Tolerance: how wide the color range is around the chosen key color.
Edge Softness: the blur/feather around edges for seamless compositing.
Color Spill: reduce any green or color cast on the foreground subject.
Brightness / Contrast: separate sliders for foreground and background.

5.	Preview
Click “Preview Composited Video” to watch the entire video with the background replaced.
If “Reverse Background” is checked, the background video frames are played in reverse.
Expect some delay of the preview video on lower-performing devices (final export after processing is standard speed).

6.	Export
Click “Export Composited Video” to render and save the final output.

## Compatibility

Mac, Windows, Linux

## Credits & License

Author: Anelia Gaydardzhieva (https://github.com/Anelia1)

(c) 2025, MIT License

## Contact

For questions, suggestions, or contributions, please open an issue in this repository or reach out via GitHub. Feedback is welcomed to further showcase the potential of this Chroma Key Compositor Demo App.
