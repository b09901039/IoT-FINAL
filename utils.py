import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

def get_frame_from_photo(path):
    frame = cv2.imread(path)
    if frame is None:
        print("get_frame_from_photo() failed")
    return frame

def get_frame_frome_video(path):
    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        print("get_frame_from_video() failed")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"width: {width}, height: {height}, fps: {fps}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        yield frame, timestamp_ms

    cap.release()

def process_frame(frame):
    try:
        show_frame(frame)
        frame = frame.copy()
        processed_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        processed_frame = cv2.GaussianBlur(processed_frame, (5, 5), 0)
        processed_frame = cv2.normalize(processed_frame, None, 0, 255, cv2.NORM_MINMAX)
        show_frame(processed_frame, "gray")
        return processed_frame
    except:
        print("process_frame() failed")
        return frame

def show_frame(frame, cmap=None):
    return
    plt.figure(figsize=(12, 8))
    plt.imshow(frame, cmap=cmap)
    plt.axis("off")
    plt.show()

def mark_cross(frame, x, y, size=8, color=(255, 0, 0), thickness=2):
    cv2.line(frame, (x - size, y - size), (x + size, y + size), color, thickness)
    cv2.line(frame, (x - size, y + size), (x + size, y - size), color, thickness)
    return frame

def add_text(frame, text, x, y, font_scale=0.8, color=(255, 0, 0), thickness=2):
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)
    return frame


def crop_keyboard(frame, n_scanlines=100, white_threshold=200, min_transactions=35, min_white_ratio=0.3):
    processed_frame = process_frame(frame)

    height, width = processed_frame.shape
    scanline_positions = np.linspace(0, height - 1, n_scanlines).astype(int)
    key_areas = []

    for y in scanline_positions:
        scanline = processed_frame[y, :]

        binary_line = (scanline > white_threshold).astype(int)
        diff = np.abs(np.diff(binary_line))
        transitions = np.sum(diff)
        white_ratio = np.sum(binary_line) / width

        if transitions > min_transactions and white_ratio > min_white_ratio:
            key_areas.append(y)
    if key_areas:
        top = max(0, min(key_areas) + int(height * 1 / n_scanlines))
        bottom = min(height, max(key_areas) - int(height * 1 / n_scanlines))
        return True, [frame[top:bottom, :], top, bottom]
        # return frame[top:bottom, :], top, bottom
    else:
        print("keyboard not found")
        return False, []
        # return None