import cv2
import requests
import time
import numpy as np
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


class VideoStreamApp:
	def __init__(self, root, stream_url):
		self.root = root
		self.root.title("Video Stream App")

		self.stream_url = stream_url
		self.is_recording = False
		self.out = None
		self.fps_video = 30
		self.frame_width = 640
		self.frame_height = 480
		self.motion_blur_time = None
		self.fps = 0
		self.frame_count = 0
		self.start_time = time.time()
		self.running = True

		self.fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')

		try:
			self.stream = requests.get(self.stream_url, stream=True)
			if self.stream.status_code != 200:
				raise ConnectionError(f"Failed to connect to stream. Status code: {self.stream.status_code}")
		except Exception as e:
			messagebox.showerror("Error", f"Could not connect to video stream: {e}")
			self.root.destroy()
			return

		# Create GUI elements
		self.video_label = tk.Label(self.root)
		self.video_label.pack()

		self.control_frame = tk.Frame(self.root)
		self.control_frame.pack()

		self.record_button = tk.Button(self.control_frame, text="Start Recording", command=self.toggle_recording)
		self.record_button.grid(row=0, column=0, padx=10, pady=10)

		self.quit_button = tk.Button(self.control_frame, text="Quit", command=self.quit_app)
		self.quit_button.grid(row=0, column=1, padx=10, pady=10)

		self.byte_buffer = b''
		time.sleep(5)
		self.update_stream()

	def calculate_blur(self, frame):
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		laplacian = cv2.Laplacian(gray, cv2.CV_64F)
		return laplacian.var()

	def detect_motion_blur(self, frame, threshold=200):
		blur_score = self.calculate_blur(frame)
		return blur_score < threshold

	def process_frame(self, frame):
		# Process the frame (rotate, flip, and add overlays)
		frame = cv2.rotate(frame, cv2.ROTATE_180)
		frame = cv2.flip(frame, 1)

		if self.detect_motion_blur(frame):
			self.motion_blur_time = time.time()

		if self.motion_blur_time and time.time() - self.motion_blur_time < 1.0:
			cv2.putText(frame, "Motion Blur Detected!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

		if self.is_recording:
			if self.out is None:
				current_datetime = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
				output_filename = f"output_{current_datetime}.mp4"
				self.out = cv2.VideoWriter(output_filename, self.fourcc, self.fps_video,
										(self.frame_width, self.frame_height))
			self.out.write(frame)

		fps_text = f"{self.fps:3.0f} FPS"
		cv2.putText(frame, fps_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

		return frame
	
	def update_stream(self):
		try:
			for chunk in self.stream.iter_content(chunk_size=1024, decode_unicode=False):
				if not chunk:
					print("Empty chunk received, stream may have ended")
					break

				self.byte_buffer += chunk

				start_index = self.byte_buffer.find(b'\xff\xd8')  # JPEG start marker
				end_index = self.byte_buffer.find(b'\xff\xd9')    # JPEG end marker

				if start_index != -1 and end_index != -1:
					jpg_frame = self.byte_buffer[start_index:end_index + 2]
					self.byte_buffer = self.byte_buffer[end_index + 2:]

					frame = cv2.imdecode(np.frombuffer(jpg_frame, np.uint8), cv2.IMREAD_COLOR)
					if frame is not None:
						frame = self.process_frame(frame)
						image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
						image = Image.fromarray(image)
						image = ImageTk.PhotoImage(image)

						self.video_label.configure(image=image)
						self.video_label.image = image

						self.frame_count += 1
						elapsed_time = time.time() - self.start_time
						if elapsed_time >= 1.0:
							self.fps = self.frame_count
							self.frame_count = 0
							self.start_time = time.time()

					break  # Process one frame per loop iteration

			# Schedule the next update
			if self.running:
				self.root.after(50, self.update_stream)

		except requests.exceptions.RequestException as e:
			print(f"Stream error: {e}")
			self.root.after(1000, self.update_stream) 

	def toggle_recording(self):
		self.is_recording = not self.is_recording
		if self.is_recording:
			self.record_button.config(text="Stop Recording")
		else:
			self.record_button.config(text="Start Recording")
			if self.out:
				self.out.release()
				self.out = None

	def quit_app(self):
		self.running = False
		if self.out:
			self.out.release()
		self.stream.close()
		self.root.destroy()


if __name__ == "__main__":
	IP = '192.168.126.100'
	stream_url = f"http://{IP}:5000/video_feed"

	root = tk.Tk()
	app = VideoStreamApp(root, stream_url)
	root.mainloop()
