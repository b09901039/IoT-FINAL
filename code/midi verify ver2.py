import mido
import tkinter as tk
import time

class MIDIComparer:
    def __init__(self, original_midi_path, played_midi_path, bpm=100, tolerance=0.1):
        self.original_midi = mido.MidiFile(original_midi_path)
        self.played_midi = mido.MidiFile(played_midi_path)
        self.bpm = bpm
        self.ticks_per_beat = self.original_midi.ticks_per_beat
        self.seconds_per_tick = 60 / (bpm * self.ticks_per_beat)
        self.tolerance = tolerance
        self.note_height = 10  # Height of note bars in the piano roll

        # Initialize tkinter window
        self.window = tk.Tk()
        self.window.title("MIDI Piano Roll Comparison")
        self.canvas = tk.Canvas(self.window, width=1000, height=400, bg="black")
        self.canvas.pack()

    def parse_midi(self, midi_file):
        """Parses a MIDI file and extracts note events with time."""
        events = []
        time_elapsed = 0
        for track in midi_file.tracks:
            for msg in track:
                time_elapsed += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    time_in_seconds = time_elapsed * self.seconds_per_tick
                    events.append({'time': time_in_seconds, 'note': msg.note, 'velocity': msg.velocity})
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

    def replay(self):
        """Replay mode: compares entire MIDI files and visualizes the notes."""
        original_events = self.parse_midi(self.original_midi)
        played_events = self.parse_midi(self.played_midi)

        # Start visualization
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
            time.sleep(0.05)  # Simulate real-time delay

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
        played_midi_path='Piano Video/Twinkle Twinkle Little Star/Twinkle Twinkle Little Star BPM100 C5 test.mid',
        bpm=100,
        tolerance=0.15
    )

    mode = 'replay'  # Change to 'realtime' for real-time mode
    if mode == 'replay':
        comparer.replay()
    elif mode == 'realtime':
        comparer.realtime()
