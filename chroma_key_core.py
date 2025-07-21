"""
chroma_key_core.py

Core logic for chroma key compositing

Author: Anelia Gaydardzhieva (https://github.com/anphiriel)
(c) 2025, MIT License 

This module provides core routines for chroma-key (greenscreen) compositing,
as well as related image-processing functions. It is designed to be used by
the ChromaKeyGUI in a separate file, ensuring a clean separation of concerns.
"""

import cv2
import numpy as np


def perform_chroma_key(
    frame: np.ndarray,
    bg_source,
    bg_is_video: bool,
    bg_color_bgr: tuple,
    tolerance: int,
    softness: int,
    color_spill: int
) -> np.ndarray:
    """
    Perform chroma-key compositing on a single frame with a given background

    :param frame:            The current foreground frame (NumPy array, BGR)
    :param bg_source:        Either a cv2.VideoCapture (if bg_is_video=True) or a NumPy array (if bg_is_video=False)
    :param bg_is_video:      Flag indicating whether bg_source is a video capture or an image
    :param bg_color_bgr:     The target color to remove, in BGR form (e.g., (0,255,0) for green)
    :param tolerance:        The hue tolerance around the target color
    :param softness:         The blur/feather amount on edges
    :param color_spill:      How much green/cast to remove from the foreground. 0 means none
    :return:                 A composited frame (NumPy array, BGR)
    """
    if bg_source is None:
        return frame

    h, w = frame.shape[:2]

    if bg_is_video:
        ret, bg_frame = bg_source.read()
        if not ret:
            bg_source.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, bg_frame = bg_source.read()
        if not ret:
            return frame
        bg_resized = cv2.resize(bg_frame, (w, h))
    else:
        bg_resized = cv2.resize(bg_source, (w, h))

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    target_hsv = cv2.cvtColor(np.uint8([[bg_color_bgr]]), cv2.COLOR_BGR2HSV)[0][0]

    lower_bound = np.array([max(0, target_hsv[0] - tolerance), 50, 50])
    upper_bound = np.array([min(180, target_hsv[0] + tolerance), 255, 255])
    mask = cv2.inRange(hsv, lower_bound, upper_bound)

    alpha = mask.astype(np.float32) / 255.0
    blur_size = max(1, softness * 4 + 1)
    alpha = cv2.GaussianBlur(alpha, (blur_size, blur_size), 0)

    alpha_3 = cv2.merge([alpha, alpha, alpha])
    fg = alpha_3 * bg_resized.astype(np.float32)
    bgf = (1.0 - alpha_3) * frame.astype(np.float32)
    combined = fg + bgf

    if color_spill > 0:
        combined[:, :, 1] = np.clip(combined[:, :, 1] - color_spill, 0, 255)

    return np.clip(combined, 0, 255).astype(np.uint8)
