import time
import cv2
from picamera2 import Picamera2
from flask import Flask, Response

app = Flask(__name__)
camera = Picamera2()

# frame_count = 0
# start_time = time.time()

# res=(1920, 1080)
res=(1296, 972)
# res=(640, 480)
framerate=60

# camera_config = camera.create_video_configuration(main={"size": (640, 480)})
camera_config = camera.create_video_configuration(
	{"size": res},
	lores={"size": res},
	controls={"FrameRate": framerate},
	buffer_count=1
)

# camera_config = camera.create_video_configuration(main={"size": (1296, 972 )})
# camera_config = camera.create_video_configuration(main={"size": (1920, 1080)})

camera.configure(camera_config)
camera.start()

def generate_frames():
	frame_count = 0
	start_time = time.time()

	while True:
		frame = camera.capture_array()  # Capture the frame from the camera

		frame = cv2.flip(frame, 0)  # Flip the frame vertically
		frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert to RGB
		
		# Encode the frame as JPEG
		_, jpeg_frame = cv2.imencode('.jpg', frame)
		yield (b'--frame\r\n'
			b'Content-Type: image/jpeg\r\n\r\n' + jpeg_frame.tobytes() + b'\r\n')

		# Calculate FPS
		frame_count += 1
		elapsed_time = time.time() - start_time
		if elapsed_time >= 1.0:  # Every second
			fps = frame_count / elapsed_time
			print(f"FPS: {fps:.2f}")
			frame_count = 0
			start_time = time.time()

def generate_frames_fps():
	frame_count = 0
	start_time = time.time()

	while True:
		frame = camera.capture_array()  # Capture the frame from the camera

		frame = cv2.flip(frame, 0)  # Flip the frame vertically
		frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert to RGB
		
		# Encode the frame as JPEG
		_, jpeg_frame = cv2.imencode('.jpg', frame)
		# Calculate FPS
		frame_count += 1
		# elapsed_time = time.time() - start_time
		# if elapsed_time >= 1.0:  # Every second
		# 	fps = frame_count / elapsed_time
		# 	print(f"FPS: {fps:.2f}")
		# 	frame_count = 0
		# 	start_time = time.time()

@app.route('/video_feed')
def video_feed():
	return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
	try:
		# generate_frames_fps()
		app.run(host='0.0.0.0', port=5000, threaded=True)
	except KeyboardInterrupt:
		camera.stop()
