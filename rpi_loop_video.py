import cv2

# Path to the video file
video_path = 'Twinkle Twinkle Little Star/Twinkle Twinkle Little Star 1296x972 Correct.mp4'  # Replace with your video file path
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

# Get the video FPS
fps = cap.get(cv2.CAP_PROP_FPS)
print(f'{fps}')
frame_delay = int(1000 / 30) 

while True:
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue
    cv2.imshow('Video Frame', frame)
    key = cv2.waitKey(frame_delay) & 0xFF
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
