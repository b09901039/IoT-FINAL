import mido
import tkinter as tk
import time
from threading import Thread, Event, Lock
import pygame
from mido import MidiFile
import numpy as np

class MIDIComparer:
	def __init__(self, original_midi_path, played_midi_path, bpm=100, tolerance=0.1):
		self.original_midi_path = original_midi_path
		self.played_midi_path = played_midi_path
		self.bpm = bpm
		self.ticks_per_beat = mido.MidiFile(original_midi_path).ticks_per_beat
		self.tolerance = tolerance
		self.note_height = 10  # Height of note beats in the piano roll
		self.seconds_per_tick = self.calculate_seconds_per_tick()

		# Initialize metronome
		self.metronome_running = False
		self.metronome_bpm = bpm

		self.NOTE_ON = set([])	
		self.start_time = time.time()
		self.count = 0
		self.last_beat = -1
		self.bar = 0
		self.offset_beat_test = 4
		self.elapsed_time = None
		self.elapsed_beat = None

		# Initialize pygame mixer for sound
		pygame.init()
		pygame.mixer.init()
		self.metronome_sound = pygame.mixer.Sound("mtick.wav") 

		# Initialize tkinter window
		self.window = tk.Tk()
		self.window.geometry("1000x600")
		self.window.title("MIDI Piano Roll Comparison")
		self.canvas = tk.Canvas(self.window, width=800, height=400, bg="black")
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

		self.golden_note_label = tk.Label(self.window, text="", fg="red", bg="black", font=("Arial", 14))
		self.golden_note_label.pack()
		self.golden_note_label.config(text=f"")

		self.test_note_label = tk.Label(self.window, text="", fg="red", bg="black", font=("Arial", 14))
		self.test_note_label.pack()



		self.lock = Lock()

		self.run_metronome_thread = Thread(target=self.run_metronome, daemon=True)
		self.run_metronome_thread.start()

		self.replay_original_thread = Thread(target=self.replay_original, daemon=True)
		self.replay_original_thread.start()

		self.replay_test_thread = Thread(target=self.replay_test, daemon=True)
		self.replay_test_thread.start()

		self.replay_original_event = Event()
		self.replay_original_running = False


		
		self.window.mainloop()

	def calculate_seconds_per_tick(self):
		return 60 / (self.bpm * self.ticks_per_beat)

	def update_bpm(self, new_bpm):
		"""Update BPM dynamically."""
		self.bpm = int(new_bpm)
		self.metronome_bpm = self.bpm
		self.seconds_per_tick = self.calculate_seconds_per_tick()
		# self.bpm_label.config(text=f"BPM: {self.bpm}")

	def parse_midi(self, midi_file_path):
		"""Parses a MIDI file and extracts note events with time."""
		midi_file = MidiFile(midi_file_path)
		events = []
		time_elapsed = 0
		
		# print(f"midi_file.ticks_per_beat: {midi_file.ticks_per_beat}")
		# print(f"self.ticks_per_beat: {self.ticks_per_beat}")
		# print(f"self.seconds_per_tick: {self.seconds_per_tick}")
		# print(f"self.bpm: {self.bpm}")

		# print(f"len(midi_file.tracks): {len(midi_file.tracks)}")
		for track in midi_file.tracks:
			# print(f"len(track): {len(track)}")
			for msg in track:
				time_elapsed += msg.time
				# print(f"msg.time: {msg.time}")
				# continue
				if msg.type == 'note_on' and msg.velocity > 0:
					# time_in_seconds = time_elapsed * self.seconds_per_tick
					# events.append({'time': time_in_seconds, 'note': msg.note})
					# print(f"note_on: {msg.note}, time_elapsed: {time_elapsed}, time_in_seconds: {time_in_seconds}")
					# print(f"note_on: {msg.note}, time_elapsed: {time_elapsed}")

					events.append({
						'beat': time_elapsed/self.ticks_per_beat, 
						'note': msg.note,
						'type': msg.type
					})
					# print(f"note_on: {msg.note}, 'beat': {time_elapsed/self.ticks_per_beat}")
				if msg.type == 'note_off':
					# time_in_seconds = time_elapsed * self.seconds_per_tick
					# events.append({'time': time_in_seconds, 'note': msg.note})	
					
					events.append({
						'beat': time_elapsed/self.ticks_per_beat, 
						'note': msg.note,
						'type': msg.type
					})
					# print(f"note_on: {msg.note}, 'beat': {time_elapsed/self.ticks_per_beat}")
				
		# print(f"events:\n {events}")

		# for track in midi_file.tracks:
		# 	time = 0  # Time in ticks
		# 	for msg in track:
		# 		time += msg.time  # Accumulate the time in ticks
		# 		time_in_beats = time / ticks_per_beat  # Convert ticks to beats

		# 		# Plotting Note On and Note Off events
		# 		if msg.type == 'note_on' and msg.velocity > 0:
		# 			plt.scatter(time_in_beats, msg.note, color='green', label='Note On' if 'Note On' not in plt.gca().get_legend_handles_labels()[1] else "")
		# 		elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
		# 			plt.scatter(time_in_beats, msg.note, color='red', label='Note Off' if 'Note Off' not in plt.gca().get_legend_handles_labels()[1] else "")


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
		self.feedback_label.config(text=f"--.--")
		self.metronome_running = True
		while True:			
			# if self.metronome_running:
			# 	self.metronome_sound.play()
			# 	time.sleep(60 / self.metronome_bpm)
			# else:
			# 	time.sleep(0.1)
			self.count += 1
			
			self.elapsed_time = time.time() - self.start_time
			self.elapsed_beat = self.elapsed_time / (60 / self.bpm)

			if int(np.floor(self.elapsed_beat)) >= self.offset_beat_test: 

				if not self.replay_original_running:
					self.replay_original_running = True
					self.replay_original_event.set()


				self.beat = int(np.floor(self.elapsed_beat)) % 4
				if self.beat == 0 and self.last_beat == 3: 
					self.bar += 1	
				if self.beat != self.last_beat and self.metronome_running:
					self.metronome_sound.play()
				self.feedback_label.config(text=f"{self.bar}.{self.beat}")
				self.last_beat = self.beat

			self.window.update_idletasks()
			self.window.update()



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
		"""Draw the piano roll axes with MIDI note labels and beat numbers."""
		# Vertical axis (MIDI note names)
		for i in range(21, 109):  # MIDI notes from A0 (21) to C8 (108)
			y = 400 - (i - 60) * self.note_height
			note_name = self.get_note_name(i)  # MIDI note name
			self.canvas.create_text(30, y - self.note_height // 2, text=note_name, fill="white", anchor="e")
		
		# Horizontal axis (beat numbers)
		for beat in range(9):  # 8 visible beats + 1 extra for scrolling
			x = beat * (1000 / 8)
			self.canvas.create_text(x + 50, 380, text=f"beat {beat + 1}", fill="white", anchor="n")

	# def scroll_and_draw(self, events, elapsed_time, offset):
	# 	"""Scroll the notes and draw them in the piano roll."""
	# 	self.canvas.delete("all")  # Clear previous frame
	# 	self.draw_axes()  # Redraw axes
	# 	for event in events:
	# 		self.metronome_running = True
	# 		note_time = event['time'] - elapsed_time
	# 		if 0 <= note_time < 8 * (60 / self.bpm):  # Only display notes within the visible 8-beat range
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


		print(f"events: {type(played_events)}")
		print(f"events: {len(played_events)}")

		print(f"events: {type(played_events[0])}")
		print(f"events: {played_events[0]}")

		return
		start_time = time.time()
		while True:
			elapsed_time = time.time() - start_time
			for event in played_events:
				print(f"events: {event}") 
				continue
			# if elapsed_time > 1:
				# print(f"elapsed_time: {elapsed_time}")
				# self.scroll_and_draw(played_events, elapsed_time, offset=0)
			# self.window.update_idletasks()
			# self.window.update()
			time.sleep(0.01)  # Smooth scrolling


	def scroll_and_draw_original(self):
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
		return
		
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

	# def check_note(self, elapsed_beat, played_event):
	# 	golden_events = self.parse_midi(self.played_midi_path)
	# 	print(f"elapsed_beat: {elapsed_beat}")
	# 	print(f"played_event: {played_event}")

	# 	for event in golden_events:
	# 		print(event)
 
	def replay_original(self):
		"""Replay mode: visualizes the played MIDI notes with scrolling."""
		played_events = self.parse_midi(self.played_midi_path)
		golden_events = self.parse_midi(self.played_midi_path)

		event_index = 0		
		start_time = None
		offset_beat = 4

		while True:
			if self.replay_original_event.is_set():
				start_time = time.time()
				self.replay_original_event.clear()
				event_index = 0		
			if start_time == None: continue
			elapsed_time = time.time() - start_time
			elapsed_beat = elapsed_time / (60 / self.bpm)

			# if event_index < len(played_events):
			# 	if elapsed_beat - offset_beat > played_events[event_index]['beat']:
			# 		if played_events[event_index]['type'] == 'note_on':
			# 			self.NOTE_ON.add(played_events[event_index]['note'])
			# 			break
			# 		elif played_events[event_index]['type'] == 'note_off':
			# 			self.NOTE_ON.remove(played_events[event_index]['note']) 
							
			# 		event_index += 1
			# 		self.test_note_label.config(text=f"{sorted(self.NOTE_ON)}")
			# else: 
			# 	start_time = None
			# 	event_index = 0	

			if event_index < len(golden_events):
				if elapsed_beat - offset_beat > golden_events[event_index]['beat']:
					if golden_events[event_index]['type'] == 'note_on':
						self.NOTE_ON.add(golden_events[event_index]['note'])
						break
					elif golden_events[event_index]['type'] == 'note_off':
						self.NOTE_ON.remove(golden_events[event_index]['note']) 
							
					event_index += 1
					self.golden_note_label.config(text=f"{sorted(self.NOTE_ON)}")
			else: 
				start_time = None
				event_index = 0		

	def replay_test(self):
		while True:
			with self.lock:
				if not self.NOTE_ON:
					self.test_note_label.config(text=f"{sorted(self.NOTE_ON)}")
					# print(f"{self.NOTE_ON}")



	def replay_backup(self):
		"""Replay mode: visualizes the played MIDI notes with scrolling."""
		played_events = self.parse_midi(self.played_midi_path)

		# NOTE_ON = set([])
		# NOTE_ON.add('4')
		# print(f"NOTE_ON: {NOTE_ON}")

		print(f"events: {type(played_events)}")
		print(f"events: {len(played_events)}")

		print(f"events: {type(played_events[0])}")
		print(f"events: {played_events[0]}")


		print(f"self.bpm: {self.bpm}")
		# print(f"self.bpm: {self.seconds_per_tick / self.bpm}")

		# for event in played_events:
		# 	print(f"events: {event}")

		event_index = 0
		current_event = played_events[0]
		current_event = played_events[1]
		# self.seconds_per_tick = 60 / (self.bpm * self.ticks_per_beat)
		# return
		start_time = time.time()
		count = 0
		last_beat = 0
		bar = 0

		offset_beat = 4
		self.test_note_label.config(text=f"{self.NOTE_ON}")
		while True:
			count += 1
			# print(f"count: {count}") 
			# self.metronome_running = True
			self.scroll_and_draw_original()
			elapsed_time = time.time() - start_time
			elapsed_beat = elapsed_time / (60 / self.bpm)

			if int(np.floor(elapsed_beat)) >= offset_beat: 
				beat = int(np.floor(elapsed_beat)) % 4
				if beat == 0 and last_beat == 3: bar += 1
				self.feedback_label.config(text=f"{bar}.{beat}")
				last_beat = beat

			if event_index < len(played_events):
				if elapsed_beat - offset_beat*2 > played_events[event_index]['beat']:

					# print(f"elapsed_beat: {elapsed_beat}") 
					# print(f"elapsed_beat: {played_events[event_index]}") 
					if played_events[event_index]['type'] == 'note_on':
						self.NOTE_ON.add(played_events[event_index]['note'])
						# print(f"NOTE_ON: {self.NOTE_ON}") 
					elif played_events[event_index]['type'] == 'note_off':
						self.NOTE_ON.remove(played_events[event_index]['note'])
					# print(f"elapsed_beat: {played_events[event_index]['beat']}") 
					event_index += 1

					# print(f"self.NOTE_ON: {self.NOTE_ON}") 
					self.test_note_label.config(text=f"{sorted(self.NOTE_ON)}")	
				# print(f"elapsed_time: {elapsed_time}, elapsed_beat: {elapsed_beat}") 
				# break	
					# self.scroll_and_draw(played_events, elapsed_time, offset=0)
			# self.window.update_idletasks()
			# self.window.update()
			# if elapsed_time > 1:
			# 	break
			# time.sleep(0.01)  # Smooth scrolling
		

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

	# comparer.replay_original()
