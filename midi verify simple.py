import mido
import tkinter as tk
import time
from threading import Thread, Event, Lock
import pygame
from mido import MidiFile
import numpy as np

class MIDIComparer:
	def __init__(self, original_midi_path, test_midi_path, bpm=100, tolerance=0.1):
		self.original_midi_path = original_midi_path
		self.test_midi_path = test_midi_path
		self.bpm = bpm
		self.ticks_per_beat = mido.MidiFile(original_midi_path).ticks_per_beat
		self.tolerance = tolerance
		self.note_height = 10  # Height of note beats in the piano roll
		self.seconds_per_tick = self.calculate_seconds_per_tick()

		# Initialize metronome
		self.metronome_running = False
		self.metronome_bpm = bpm

		self.NOTE_ON_test = set([])	
		self.NOTE_ON_golden = set([])	
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
		self.window.geometry("200x250")
		self.window.title("MIDI Piano Roll Comparison")
		# self.canvas = tk.Canvas(self.window, width=800, height=400, bg="black")
		# self.canvas.pack()

		# BPM slider and label
		self.bpm_label = tk.Label(self.window, text=f"BPM: {self.bpm}", fg="white", bg="black")
		self.bpm_label.pack()
		self.bpm_slider = tk.Scale(self.window, from_=50, to=200, orient='horizontal', command=self.update_bpm)
		self.bpm_slider.set(self.bpm)
		self.bpm_slider.pack()

		# Note feedback display
		self.feedback_label = tk.Label(self.window, text="", fg="white", bg="black", font=("Arial", 14))
		self.feedback_label.pack()

		self.golden_note_label = tk.Label(self.window, text="", fg="white", bg="black", font=("Arial", 14))
		self.golden_note_label.pack()
		self.golden_note_label.config(text=f"")

		self.test_note_label = tk.Label(self.window, text="", fg="white", bg="black", font=("Arial", 14))
		self.test_note_label.pack()

		self.realtime_note_label = tk.Label(self.window, text="", fg="white", bg="black", font=("Arial", 14))
		self.realtime_note_label.pack()

		self.note_names = [
			'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
		]	
		self.active_notes = set()
		self.midi_in = None
		self.available_midi_devices = mido.get_input_names()
		self.selected_midi_device = tk.StringVar(value="No MIDI Input")
		self.control_frame = tk.Frame(self.window, bg="gray")
		self.control_frame.pack()
		self.midi_dropdown = tk.OptionMenu(
			self.control_frame, 
			self.selected_midi_device, 
			"No MIDI Input", 
			*self.available_midi_devices, 
			command=self.select_midi_device
		)
		self.midi_dropdown.config(bg="gray", fg="white")
		self.midi_dropdown.grid(row=0, column=2, padx=10)

		self.lock = Lock()

		self.run_metronome_thread = Thread(target=self.run_metronome, daemon=True)
		self.run_metronome_thread.start()
		self.replay_original_thread = Thread(target=self.replay_original, daemon=True)
		self.replay_original_thread.start()

		self.replay_original_event = Event()
		self.replay_original_running = False
		self.run_metronome_event = Event()
		self.run_metronome_running = False
		
		self.window.mainloop()


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
				return
			try:
				if self.midi_in:
					self.midi_in.close()
				self.midi_in = mido.open_input(selected_device)
				print(f"Selected MIDI device: {selected_device}")
			except Exception as e:
				print(f"Failed to open MIDI device '{selected_device}': {e}")
				self.midi_in = None

	def midi_to_note_name(self, midi_number):
		octave = midi_number // 12 - 1   
		note = self.note_names[midi_number % 12] 
		return f"{note}{octave}"


	def calculate_seconds_per_tick(self):
		return 60 / (self.bpm * self.ticks_per_beat)

	def update_bpm(self, new_bpm):
		"""Update BPM dynamically."""
		self.bpm = int(new_bpm)
		self.metronome_bpm = self.bpm
		self.seconds_per_tick = self.calculate_seconds_per_tick()
		# self.bpm_label.config(text=f"BPM: {self.bpm}")

	def parse_midi(self, midi_file_path):
		midi_file = MidiFile(midi_file_path)
		events = []
		time_elapsed = 0
		for track in midi_file.tracks:
			for msg in track:
				time_elapsed += msg.time
				if msg.type == 'note_on' and msg.velocity > 0:
					events.append({
						'beat': time_elapsed/self.ticks_per_beat, 
						'note': msg.note,
						'type': msg.type
					})
				if msg.type == 'note_off':
					
					events.append({
						'beat': time_elapsed/self.ticks_per_beat, 
						'note': msg.note,
						'type': msg.type
					})

		return events

	def compare_notes(self, test_event, original_events):
		"""Checks if the test note matches any note in the original with tolerance."""
		for original_event in original_events:
			if abs(original_event['time'] - test_event['time']) <= self.tolerance:
				if test_event['note'] == original_event['note']:
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

		while not self.run_metronome_event.is_set():	
			continue

		self.start_time = time.time()		
		while True:		
			self.elapsed_time = time.time() - self.start_time
			self.elapsed_beat = self.elapsed_time / (60 / self.bpm)

			# if int(np.floor(self.elapsed_beat)) >= self.offset_beat_test: 

				# if not self.replay_original_running:
				# 	self.replay_original_running = True
				# 	self.replay_original_event.set()


			self.beat = int(np.floor(self.elapsed_beat)) % 4
			if self.beat == 0 and self.last_beat == 3: 
				self.bar += 1	
			if self.beat != self.last_beat and self.metronome_running:
				self.metronome_sound.play()
			self.feedback_label.config(text=f"{self.bar-1}.{self.beat}")
			self.last_beat = self.beat

			

			self.window.update_idletasks()
			self.window.update()


	def get_note_name(self, note_number):
		"""Converts a MIDI note number to its note name."""
		note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
		octave = (note_number // 12) - 1
		note = note_names[note_number % 12]
		return f"{note}{octave}"

	def replay_original(self):
		"""Replay mode: visualizes the test MIDI notes with scrolling."""
		test_events = self.parse_midi(self.test_midi_path)
		golden_events = self.parse_midi(self.test_midi_path)

		test_event_index = 0		
		golden_event_index = 0		
		start_time = None
		offset_beat = 4

		while True:
			if self.midi_in:
				for msg in self.midi_in.iter_pending():
					if msg.type == 'note_on' and msg.velocity > 0:
						if not self.replay_original_running:
							self.replay_original_running = True
							self.replay_original_event.set()

						if not self.run_metronome_running:
							self.run_metronome_running = True
							self.run_metronome_event.set()

						# note_name = self.midi_to_note_name(msg.note)
						self.active_notes.add(msg.note)
					elif msg.type in ('note_off', 'note_on') and msg.velocity == 0:
						# note_name = self.midi_to_note_name(msg.note)
						self.active_notes.discard(msg.note)
			if self.replay_original_event.is_set():
				start_time = time.time()
				self.replay_original_event.clear()
				test_event_index = 0		

			if start_time == None: continue
			elapsed_time = time.time() - start_time
			elapsed_beat = elapsed_time / (60 / self.bpm)

			# if test_event_index < len(test_events):
			# 	if elapsed_beat - offset_beat > test_events[test_event_index]['beat']:
			# 		with self.lock:
			# 			if test_events[test_event_index]['type'] == 'note_on':
			# 				self.NOTE_ON_test.add(test_events[test_event_index]['note'])							
			# 			elif test_events[test_event_index]['type'] == 'note_off':
			# 				self.NOTE_ON_test.remove(test_events[test_event_index]['note']) 
			# 		test_event_index += 1
			# 		self.test_note_label.config(text=f"{sorted(self.NOTE_ON_test)}")
			# else: 
			# 	start_time = None
			# 	test_event_index = 0	

			if golden_event_index < len(golden_events):
				if elapsed_beat - offset_beat > golden_events[golden_event_index]['beat']:
					with self.lock:
						if golden_events[golden_event_index]['type'] == 'note_on':
							self.NOTE_ON_golden.add(golden_events[golden_event_index]['note'])
						elif golden_events[golden_event_index]['type'] == 'note_off':
							self.NOTE_ON_golden.remove(golden_events[golden_event_index]['note']) 
					golden_event_index += 1
					# self.golden_note_label.config(text=f"{sorted(self.NOTE_ON_golden)}")
			else: 
				start_time = None
				golden_event_index = 0	

			Correct = True 
			for note in self.active_notes:				
				if note not in self.NOTE_ON_golden:
					Correct = False 
					break				

			if Correct:
				if self.active_notes:
					self.realtime_note_label.config(fg='white', text=f"{sorted(self.active_notes)}")
				else:
					self.realtime_note_label.config(fg='white', text=f"")
			else:
				if self.active_notes:
					self.realtime_note_label.config(fg='red', text=f"{sorted(self.active_notes)}")
				else:
					self.realtime_note_label.config(fg='red', text=f"")

			Missed = False 
			for note in self.NOTE_ON_golden:				
				if note not in self.active_notes:
					Missed = True 
					break	
				
			if Missed:
				if self.NOTE_ON_golden:
					self.golden_note_label.config(fg='red', text=f"{sorted(self.NOTE_ON_golden)}")
				else:
					self.golden_note_label.config(fg='red', text=f"")
			else:
				if self.NOTE_ON_golden:
					self.golden_note_label.config(fg='white', text=f"{sorted(self.NOTE_ON_golden)}")
				else:
					self.golden_note_label.config(fg='white', text=f"")


if __name__ == "__main__":
	comparer = MIDIComparer(
		original_midi_path='Piano Video/Twinkle Twinkle Little Star/Twinkle Twinkle Little Star BPM100 C5.mid',
		test_midi_path='Piano Video/Twinkle Twinkle Little Star/Twinkle Twinkle Little Star BPM100 C5.mid',
		bpm = 100,
		tolerance = 0.15
	)
