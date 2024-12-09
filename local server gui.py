import cv2
import requests
import time
import numpy as np
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import mido
import threading

from flask import Flask
from flask_socketio import SocketIO

FlaskApp = Flask(__name__)
socketio = SocketIO(FlaskApp, cors_allowed_origins="*")

class VideoStreamApp:
	def __init__(self, root, stream_url):

		self.root = root
		self.root.title("Piano Assistant Demo")

		self.stream_url = stream_url
		self.is_recording = False
		self.out = None


		self.fps_video = 30

		self.frame_width = 640
		self.frame_height = 480

		self.resolution = "1296x972"
		# self.frame_width = 1296
		# self.frame_height = 972


		self.motion_blur_time = None
		self.fps = 0
		self.frame_count = 0
		self.start_time = time.time()
		self.running = True

		# self.fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
		self.fourcc = cv2.VideoWriter_fourcc(*'mp4v') 

		self.frame = None	
		self.stream = None
		self.byte_buffer = b''

		# self.midi_device_name = 'FLkey Mini MIDI 0'
		self.note_names = [
			'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
		]		
		
		self.active_notes = set()
		self.midi_in = None
		self.available_midi_devices = mido.get_input_names()
		self.selected_midi_device = tk.StringVar(value="No MIDI Input")

		self.default_placeholder_image = ImageTk.PhotoImage(
			Image.new('RGB', (self.frame_width, self.frame_height), color='gray')
		)

		self.setup_ui()

		self.stopEvent = threading.Event()
		self.video_thread = threading.Thread(target=self.videoLoop, args=())
		self.video_thread.start()

		self.flask_thread = threading.Thread(target=self.run_flask_server, daemon=True)
		self.flask_thread.start() 

	def run_flask_server(self):
		socketio.run(FlaskApp, host="0.0.0.0", port=5001)

	def setup_ui(self):
		self.root.config(bg="gray")
		self.root.resizable(False, False)

		self.top_padding = tk.Frame(self.root, height=10, bg="gray") 
		self.top_padding.pack() 
		self.title_frame = tk.Frame(self.root, bg="gray")
		self.title_frame.pack()
		self.title_placeholder_image = ImageTk.PhotoImage(
			Image.new('RGB', (300, 100), color="gray")
		)
		self.title_label = tk.Label(
			self.title_frame, 
			image=self.title_placeholder_image, 
			width=self.frame_width, height=40,
			text="L'assistant de Piano", 
			compound='center', 
			font=("Script", 30, "bold"), 
			bg="gray",			
			fg="white",
		)
		self.title_label.pack()

		self.video_frame = tk.Frame(
			self.root, 
			width=self.frame_width, 
			height=self.frame_height,
			bg="gray",
		)
		self.video_frame.pack()		

		self.video_label = tk.Label(
			self.video_frame, 
			image=self.default_placeholder_image, 
			text="No Video Feed", 
			compound='center', 
			font=("Arial", 14), 
			bg="black", 
			fg="white"
		)
		self.video_label.pack(padx=10)

		self.control_frame = tk.Frame(self.root, bg="gray")
		self.control_frame.pack()

		self.record_button = tk.Button(
			self.control_frame, text="Start Recording", 
			command=self.toggle_recording,
			bg="gray",
			fg="white"
		)
		self.record_button.grid(row=0, column=0, padx=10, pady=10)

		self.quit_button = tk.Button(
			self.control_frame, 
			text="Quit", 
			command=self.quit_app,
			bg="gray",
			fg="white"
		)
		self.quit_button.grid(row=0, column=1, padx=10, pady=10)

		self.midi_dropdown = tk.OptionMenu(
			self.control_frame, 
			self.selected_midi_device, 
			"No MIDI Input", 
			*self.available_midi_devices, 
			command=self.select_midi_device
		)
		self.midi_dropdown.config(bg="gray", fg="white")
		self.midi_dropdown.grid(row=0, column=2, padx=10)


		self.resolutions = [(640, 480), (1296, 972)] 
		self.selected_resolution = tk.StringVar(value="640x480")

		self.resolution_dropdown = tk.OptionMenu(
			self.control_frame,
			self.selected_resolution,
			*["x".join(map(str, res)) for res in self.resolutions],
			command=self.change_resolution
		)
		self.resolution_dropdown.config(bg="gray", fg="white")
		self.resolution_dropdown.grid(row=0, column=3, padx=10)


		self.info_label = tk.Label(
			self.root,
			text="",
			font=("Arial", 14),
			bg="gray",
			fg="white",
			justify="center"
		)
		self.info_label.pack(pady=(10, 0))

	def change_resolution(self, selected_resolution):
		width, height = map(int, selected_resolution.split("x"))
		new_resolution = (width, height)
		print(f"Changing resolution to: {new_resolution}")

		# Send a request to the RPi server to update resolution
		try:
			response = requests.post(f"http://{IP}:5000/change_resolution", json={"width": width, "height": height})
			if response.status_code == 200:
				print("Resolution updated successfully on RPi server.")
			else:
				print(f"Failed to update resolution on RPi server. Status code: {response.status_code}")
		except Exception as e:
			print(f"Error changing resolution: {e}")

	def select_midi_device(self, selected_device):
		"""Handle MIDI device selection."""
		if selected_device == "No MIDI Input":
			if self.midi_in:
				self.midi_in.close()  # Close any previously opened MIDI device
				self.midi_in = None
			print("No MIDI Input selected.")
		else:
			if self.midi_in and self.midi_in.name == selected_device:
				print(f"MIDI device '{selected_device}' is already open.")
				return  # Skip reopening the same device
			try:
				if self.midi_in:
					self.midi_in.close()  # Close the current MIDI device
				self.midi_in = mido.open_input(selected_device)
				print(f"Selected MIDI device: {selected_device}")
			except Exception as e:
				print(f"Failed to open MIDI device '{selected_device}': {e}")
				self.midi_in = None


	def midi_to_note_name(self, midi_number):
		octave = midi_number // 12 - 1   
		note = self.note_names[midi_number % 12] 
		return f"{note}{octave}"

	def connect(self):

		while self.stream is None: # and not self.stopEvent.is_set():
			try:
				self.stream = requests.get(self.stream_url, stream=True, timeout=5)
				if self.stream.status_code != 200:
					raise ConnectionError(f"Failed to connect to stream. Status code: {self.stream.status_code}")
				else:
					# self.loading_animation_active = False
					# self.loading_thread.join()
					break
			except Exception as e:
				print(f"Error: {e}. Retrying...")
				time.sleep(1)

	def calculate_blur(self, frame):
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		laplacian = cv2.Laplacian(gray, cv2.CV_64F)
		return laplacian.var()

	def detect_motion_blur(self, frame, threshold=125):
		blur_score = self.calculate_blur(frame)
		return blur_score < threshold

	def process_frame(self, frame):
		frame = cv2.rotate(frame, cv2.ROTATE_180)
		frame = cv2.flip(frame, 1)

		if self.is_recording:
			cv2.putText(frame, "Recording...", (self.frame_width - 110, 40), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 255), 2, cv2.LINE_AA)
						
			if self.out is None:
				current_datetime = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")

				
				# output_filename = f"output {self.fps_video}fps{current_datetime}.mp4"
				output_filename = f"output {self.fps_video}fps {self.resolution} {current_datetime}.mp4"
				self.out = cv2.VideoWriter(
					output_filename,
					self.fourcc,
					fps=20, 
					frameSize=(1296, 972)
				)

		if self.is_recording:
			self.out.write(frame)


		frame = cv2.resize(frame, (self.frame_width, self.frame_height))

		# if self.detect_motion_blur(frame):						
		# 	self.motion_blur_time = time.time()
		# if self.motion_blur_time is not None and time.time() - self.motion_blur_time < 1.0:
		# 	cv2.putText(frame, "Motion blur detected!", (self.frame_width//2-0, 40), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 255), 2, cv2.LINE_AA)
		# 	# print("Motion blur detected!")
		# else:
		# 	self.motion_blur_time = None 
			
		if self.midi_in:
			for msg in self.midi_in.iter_pending():
				if msg.type == 'note_on' and msg.velocity > 0:  # Key pressed
					note_name = self.midi_to_note_name(msg.note)
					self.active_notes.add(note_name)
				elif msg.type in ('note_off', 'note_on') and msg.velocity == 0:  # Key released
					note_name = self.midi_to_note_name(msg.note)
					self.active_notes.discard(note_name)

			if self.active_notes:
				text_thickness = 2
				text_scale = 1
				notes_text = " ".join(sorted(self.active_notes))  
				(text_width, text_height), _ = cv2.getTextSize(notes_text, cv2.FONT_HERSHEY_SIMPLEX, text_scale, text_thickness)

				x = (self.frame_width - text_width) // 2
				y = 450 # (frame_height + text_height) // 2  
				
				cv2.putText(
					frame, 
					notes_text, 
					(x, y), 
					cv2.FONT_HERSHEY_DUPLEX, 
					text_scale, (255, 255, 255), 
					text_thickness, 
					cv2.LINE_AA,
				)

		fps_text = f"{self.fps:3.0f} FPS"
		cv2.putText(frame, fps_text, (self.frame_width - 80, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

		
		return frame
	
	def videoLoop(self):
		while not self.stopEvent.is_set():
			try:
				if self.stream is None:
					self.connect()
					self.video_label.config(
						image=self.default_placeholder_image,
						text="Loading Video Feed...",
						compound='center',
					)
					continue

				for chunk in self.stream.iter_content(chunk_size=1024):
					if self.stopEvent.is_set():
						break
					self.byte_buffer += chunk
					start_index = self.byte_buffer.find(b'\xff\xd8')
					end_index = self.byte_buffer.find(b'\xff\xd9')

					if start_index != -1 and end_index != -1:
						jpg_frame = self.byte_buffer[start_index:end_index + 2]
						self.byte_buffer = self.byte_buffer[end_index + 2:]
						try:
							frame = cv2.imdecode(np.frombuffer(jpg_frame, np.uint8), cv2.IMREAD_COLOR)
						except Exception as e:
							print(f"Failed to decode frame: {e}")
							continue

						if frame is not None:

							_, encoded_frame = cv2.imencode('.jpg', frame)
							socketio.emit('video_frame', {'frame': encoded_frame.tobytes()})

							frame = self.process_frame(frame)
							image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
							image = Image.fromarray(image)
							image = ImageTk.PhotoImage(image)

							# self.video_label.config(
							# 	width=self.frame_width, 
							# 	height=self.frame_height
							# )							
							self.video_label.config(image=image, text="")
							self.video_label.image = image



							self.frame_count += 1
							elapsed_time = time.time() - self.start_time
							if elapsed_time >= 1.0:
								self.fps = self.frame_count
								self.frame_count = 0
								self.start_time = time.time()

			except requests.exceptions.RequestException as e:
				print(f"Stream error: {e}")
				self.stream = None
				self.video_label.config(
					image=self.default_placeholder_image,
					text="Video Feed Disconnected",
					compound='center',
				)


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
		print("Closing application...")
		try:
			self.stopEvent.set()
			if self.video_thread.is_alive():
				self.video_thread.join(timeout=5) 
			if self.flask_thread.is_alive():
				self.flask_thread.join(timeout=5) 
			if self.stream:
				self.stream.close()
			if self.out:
				self.out.release()
				self.out = None
		except Exception as e:
			print(f"Error closing stream: {e}")

		if self.root:
			try:
				self.root.destroy()
			except Exception as e:
				print(f"Error destroying root: {e}")

		print("Application closed.")

@FlaskApp.route("/")
def index():
    return "Flask server is running!"

if __name__ == "__main__":
	IP = '192.168.188.100'
	stream_url = f"http://{IP}:5000/video"

	root = tk.Tk()
	app = VideoStreamApp(root, stream_url)
	root.mainloop()
