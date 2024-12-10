import time
import cv2
from picamera2 import Picamera2
from flask import Flask, Response, request
import threading

class CameraStream:
	def __init__(self, resolution=(640, 480), framerate=15):
		self.camera = Picamera2()
		self.resolution = resolution
		self.framerate = framerate  # Hardcoded FPS to 15
		self.frame_count = 0
		self.start_time = time.time()

		# Set up the camera configuration
		self.camera_config = self.camera.create_video_configuration(
			{"size": self.resolution},
			lores={"size": self.resolution},
			controls={"FrameRate": self.framerate},
			buffer_count=1
		)
		self.camera.configure(self.camera_config)

	def start(self):
		self.camera.start()

	def stop(self):
		self.camera.stop()

	def generate_frames(self):
		while True:
			frame = self.camera.capture_array()  # Capture the frame from the camera
			frame = cv2.flip(frame, 0)  # Flip the frame vertically
			frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert to RGB

			_, jpeg_frame = cv2.imencode('.jpg', frame)
			yield (b'--frame\r\n'
				b'Content-Type: image/jpeg\r\n\r\n' + jpeg_frame.tobytes() + b'\r\n')

			self.frame_count += 1
			elapsed_time = time.time() - self.start_time
			if elapsed_time >= 1.0: 
				fps = self.frame_count / elapsed_time
				print(f"FPS: {fps:.2f}")
				self.frame_count = 0
				self.start_time = time.time()


class CameraApp:
	def __init__(self):
		self.app = Flask(__name__)
		self.camera_stream = CameraStream()

		self.app.add_url_rule('/video', 'video', self.video_stream)
		self.app.add_url_rule('/pause', 'pause', self.video_pause)
		self.app.add_url_rule('/change_resolution', 'change_resolution', self.change_resolution, methods=['POST'])

	def video_pause(self):
		self.camera_stream.stop() 
		return {"message": "Video feed paused"}, 200 

	def video_stream(self):
		self.camera_stream.stop()
		self.camera_stream.resolution = (640, 480)
		self.camera_stream.camera_config = self.camera_stream.camera.create_video_configuration(
			{"size": self.camera_stream.resolution},
			lores={"size": self.camera_stream.resolution},
			controls={"FrameRate": 15},  # Hardcoded FPS to 15
			buffer_count=1
		)
		self.camera_stream.camera.configure(self.camera_stream.camera_config)
		self.camera_stream.start()
		return Response(self.camera_stream.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

	def change_resolution(self):
		data = request.json
		new_resolution = (data.get('width'), data.get('height'))
		if new_resolution in [(640, 480), (1296, 972)]:
			self.camera_stream.stop()
			self.camera_stream.resolution = new_resolution
			self.camera_stream.camera_config = self.camera_stream.camera.create_video_configuration(
				{"size": self.camera_stream.resolution},
				lores={"size": self.camera_stream.resolution},
				controls={"FrameRate": 15},  # Hardcoded FPS to 15
				buffer_count=1
			)
			self.camera_stream.camera.configure(self.camera_stream.camera_config)
			self.camera_stream.start()
			print(f"Resolution changed to: {new_resolution}")
			return {"message": "Resolution updated successfully"}, 200
		else:
			return {"error": "Invalid resolution"}, 400

	def run(self):
		try:
			self.camera_stream.start()  # Start the camera
			self.app.run(host='0.0.0.0', port=5000, threaded=True)
		except KeyboardInterrupt:
			self.camera_stream.stop()  # Stop the camera when interrupted


if __name__ == '__main__':
	camera_app = CameraApp()
	camera_app.run()
