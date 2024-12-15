import mido
import tkinter as tk
import time
import threading
import pygame
from mido import MidiFile

class MIDIComparer:
	def __init__(self, original_midi_path, played_midi_path, bpm=100, tolerance=0.1):
		self.original_midi_path = original_midi_path
		self.played_midi_path = played_midi_path
		self.bpm = bpm
		self.ticks_per_beat = mido.MidiFile(original_midi_path).ticks_per_beat
		self.tolerance = tolerance
		self.note_height = 10  # Height of note bars in the piano roll
		self.seconds_per_tick = self.calculate_seconds_per_tick()

		# Initialize metronome
		self.metronome_running = False
		self.metronome_bpm = bpm

		# Initialize pygame mixer for sound
		pygame.init()
		pygame.mixer.init()
		self.metronome_sound = pygame.mixer.Sound("mtick.wav") 

		# Initialize tkinter window
		self.window = tk.Tk()
		self.window.title("MIDI Piano Roll Comparison")
		self.canvas = tk.Canvas(self.window, width=1000, height=400, bg="black")
		self.canvas.pack()

		# BPM slider and label
		self.bpm_label = tk.Label(self.window, text=f"BPM: {self.bpm}", fg="white", bg="black")
		self.bpm_label.pack()
		self.bpm_slider = tk.Scale(self.window, from_=50, to=200, orient='horizontal', command=self.update_bpm)
		self.bpm_slider.set(self.bpm)
		self.bpm_slider.pack()

		# Note feedback display
		self.feedback_label = tk.Label(self.window, text="", fg="red", bg="black", font=("Arial", 14))
		self.feedback_label.pack()

		# Start metronome in a separate thread
		threading.Thread(target=self.run_metronome, daemon=True).start()

	def calculate_seconds_per_tick(self):
		return 60 / (self.bpm * self.ticks_per_beat)

	def update_bpm(self, new_bpm):
		"""Update BPM dynamically."""
		self.bpm = int(new_bpm)
		self.metronome_bpm = self.bpm
		self.seconds_per_tick = self.calculate_seconds_per_tick()
		self.bpm_label.config(text=f"BPM: {self.bpm}")

	def parse_midi(self, midi_file_path):
		"""Parses a MIDI file and extracts note events with time."""
		midi_file = MidiFile(midi_file_path)
		events = []
		time_elapsed = 0
		for track in midi_file.tracks:
			for msg in track:
				time_elapsed += msg.time
				if msg.type == 'note_on' and msg.velocity > 0:
					time_in_seconds = time_elapsed * self.seconds_per_tick
					events.append({'time': time_in_seconds, 'note': msg.note})
		return events

	def compare_notes(self, played_event, original_events):
		"""Checks if the played note matches any note in the original with tolerance."""
		for original_event in original_events:
			if abs(original_event['time'] - played_event['time']) <= self.tolerance:
				if played_event['note'] == original_event['note']:
					return True
		return False

	def draw_note(self, time_in_seconds, note, color, offset=0):
		"""Draws a single note as a rectangle on the canvas."""
		x = time_in_seconds * 100  # Scale time to x-axis
		y = 400 - (note - 60) * self.note_height - offset  # Align notes, middle C is around y=400
		self.canvas.create_rectangle(x, y, x+20, y-self.note_height, fill=color, outline="white")

	def run_metronome(self):
		"""Runs the metronome sound at the set BPM."""
		while True:
			if self.metronome_running:
				self.metronome_sound.play()
				time.sleep(60 / self.metronome_bpm)
			else:
				time.sleep(0.1)

	def replay(self):
		"""Replay mode: compares MIDI files and visualizes notes in real-world time."""
		original_events = self.parse_midi(self.original_midi_path)
		played_events = self.parse_midi(self.played_midi_path)

		self.metronome_running = True  # Start metronome
		start_time = time.time()
		played_index = 0

		played_len = len(played_events)
		for original_event in original_events:
			# Draw original notes in green
			elapsed_time = time.time() - start_time
			while played_index < played_len and played_events[played_index]['time'] <= elapsed_time:
				played_event = played_events[played_index]
				# Check for correctness
				if self.compare_notes(played_event, original_events):
					self.draw_note(played_event['time'], played_event['note'], "blue")
				else:
					self.draw_note(played_event['time'], played_event['note'], "red")
				played_index += 1

			self.draw_note(original_event['time'], original_event['note'], "green")
			self.window.update_idletasks()
			self.window.update()
			time.sleep(0.01) 

		self.window.mainloop()

		return
		for original_event in original_events:
			elapsed_time = time.time() - start_time
			self.draw_note(original_event['time'], original_event['note'], "green")

			while played_index < len(played_events) and played_events[played_index]['time'] <= elapsed_time:
				played_event = played_events[played_index]
				if self.compare_notes(played_event, original_events):
					self.draw_note(played_event['time'], played_event['note'], "blue")
					self.feedback_label.config(text="Correct Note!")
				else:
					self.draw_note(played_event['time'], played_event['note'], "red")
					self.feedback_label.config(text="Incorrect Note!")
				played_index += 1

			self.window.update()
			time.sleep(0.01)

		self.metronome_running = False  # Stop metronome
		self.window.mainloop()

	def get_note_name(self, note_number):
		"""Converts a MIDI note number to its note name."""
		note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
		octave = (note_number // 12) - 1
		note = note_names[note_number % 12]
		return f"{note}{octave}"
	
	def draw_axes(self):
		"""Draw the piano roll axes with MIDI note labels and bar numbers."""
		# Vertical axis (MIDI note names)
		for i in range(21, 109):  # MIDI notes from A0 (21) to C8 (108)
			y = 400 - (i - 60) * self.note_height
			note_name = self.get_note_name(i)  # MIDI note name
			self.canvas.create_text(30, y - self.note_height // 2, text=note_name, fill="white", anchor="e")
		
		# Horizontal axis (bar numbers)
		for bar in range(9):  # 8 visible bars + 1 extra for scrolling
			x = bar * (1000 / 8)
			self.canvas.create_text(x + 50, 380, text=f"Bar {bar + 1}", fill="white", anchor="n")

	# def scroll_and_draw(self, events, elapsed_time, offset):
	# 	"""Scroll the notes and draw them in the piano roll."""
	# 	self.canvas.delete("all")  # Clear previous frame
	# 	self.draw_axes()  # Redraw axes
	# 	for event in events:
	# 		self.metronome_running = True
	# 		note_time = event['time'] - elapsed_time
	# 		if 0 <= note_time < 8 * (60 / self.bpm):  # Only display notes within the visible 8-bar range
	# 			x = 1000 - (note_time * (1000 / (8 * (60 / self.bpm)))) + offset
	# 			y = 400 - (event['note'] - 60) * self.note_height
	# 			self.canvas.create_rectangle(x, y, x + 20, y - self.note_height, fill="blue", outline="white")
	
	def scroll_and_draw(self, events, elapsed_time, offset=50):
		"""Scroll the notes and draw them in the piano roll with a grid."""
		self.canvas.delete("all")  # Clear previous frame

		canvas_width = 1000  # Canvas width in pixels
		canvas_height = 400  # Canvas height in pixels
		visible_duration = 8 * (60 / self.bpm)  # Duration of visible range in seconds
		pixels_per_second = canvas_width / visible_duration

		# Draw grid lines
		for i in range(0, canvas_width, 50):  # Vertical grid lines every 50 pixels
			self.canvas.create_line(i, 0, i, canvas_height, fill="#222222", dash=(2, 2))
		for i in range(0, canvas_height, self.note_height):  # Horizontal grid lines per note height
			self.canvas.create_line(0, i, canvas_width, i, fill="#222222", dash=(2, 2))
		
		# print(f"events: {events}")
		# return
		
		for event in events:
			print(f"events: {event}") 
			continue
			
			
			self.metronome_running = True
			note_time = event['time'] - elapsed_time
			
			if 0 <= note_time <= visible_duration + 1: 
				x = canvas_width - (note_time * pixels_per_second) # + offset

				x = canvas_width - x
				y = canvas_height - (event['note'] - 60) * self.note_height

				# Draw the note rectangle
				self.canvas.create_rectangle(
					x, y, x +20, y - self.note_height, fill="blue", outline="white"
				)

		self.draw_axes()


	def replay_only_scroll(self):
		"""Replay mode: visualizes the played MIDI notes with scrolling."""
		played_events = self.parse_midi(self.played_midi_path)

		start_time = time.time()
		while True:
			elapsed_time = time.time() - start_time
			if elapsed_time > 1:
				# print(f"elapsed_time: {elapsed_time}")
				self.scroll_and_draw(played_events, elapsed_time, offset=0)
			self.window.update_idletasks()
			self.window.update()
			time.sleep(0.01)  # Smooth scrolling
			
	def replay_only(self):
		"""Replay mode: visualizes the played MIDI notes in real-world time."""
		played_events = self.parse_midi(self.played_midi_path)

		start_time = time.time()
		played_index = 0

		played_len = len(played_events)

		while played_index < played_len:
			elapsed_time = time.time() - start_time
			while played_index < played_len and played_events[played_index]['time'] <= elapsed_time:
				self.metronome_running = True
				
				played_event = played_events[played_index]
				self.draw_note(played_event['time'], played_event['note'], "blue")

				played_index += 1

			self.window.update_idletasks()
			self.window.update()
			time.sleep(0.01)  # Small delay for smooth visualization

		# self.metronome_running = False  # Stop metronome
		self.window.mainloop()

	def realtime(self):
		"""Realtime mode: listens for live MIDI input and visualizes notes."""
		original_events = self.parse_midi(self.original_midi)
		played_events = []

		with mido.open_input() as inport:
			start_time = time.time()
			for msg in inport:
				if msg.type == 'note_on' and msg.velocity > 0:
					elapsed_time = time.time() - start_time
					played_event = {'time': elapsed_time, 'note': msg.note, 'velocity': msg.velocity}
					played_events.append(played_event)

					# Check correctness
					if self.compare_notes(played_event, original_events):
						self.draw_note(elapsed_time, played_event['note'], "blue")
					else:
						self.draw_note(elapsed_time, played_event['note'], "red")

					self.window.update_idletasks()
					self.window.update()

if __name__ == "__main__":
	comparer = MIDIComparer(
		original_midi_path='Piano Video/Twinkle Twinkle Little Star/Twinkle Twinkle Little Star BPM100 C5.mid',
		played_midi_path='Piano Video/Twinkle Twinkle Little Star/Twinkle Twinkle Little Star BPM100 C5.mid',
		# played_midi_path='Piano Video/Twinkle Twinkle Little Star/Twinkle Twinkle Little Star BPM100 C5.mid',
		bpm=100,
		tolerance=0.15
	)

	# comparer.replay()
	# comparer.replay_only()
	comparer.replay_only_scroll()
