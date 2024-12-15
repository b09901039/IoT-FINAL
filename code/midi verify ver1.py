import mido
import matplotlib.pyplot as plt

class MIDIComparer:
    def __init__(self, original_midi_path, played_midi_path, bpm=100):
        self.original_midi = mido.MidiFile(original_midi_path)
        self.played_midi = mido.MidiFile(played_midi_path)
        self.bpm = bpm
        self.ticks_per_beat = self.original_midi.ticks_per_beat
        self.seconds_per_tick = 60 / (bpm * self.ticks_per_beat)

    def parse_midi(self, midi_file):
        """Parses a MIDI file and extracts note events with time."""
        events = []
        time = 0
        for track in midi_file.tracks:
            for msg in track:
                time += msg.time
                if msg.type in ['note_on', 'note_off']:
                    events.append({'time': time, 'note': msg.note, 'type': msg.type, 'velocity': msg.velocity})
        return events

    def compare_notes(self, original_events, played_events):
        """Compares original and played notes, identifying mismatched notes."""
        wrong_notes = []
        for played in played_events:
            matched = any(
                original['note'] == played['note'] and played['type'] == original['type']
                for original in original_events
            )
            if not matched:
                wrong_notes.append(played)
        return wrong_notes

    def plot_midi(self, original_events, played_events, wrong_notes):
        """Plots the original and played MIDI notes, marking incorrect notes."""
        plt.figure(figsize=(14, 7))

        # Plot original MIDI notes
        for event in original_events:
            time_in_beats = event['time'] / self.ticks_per_beat
            color = 'green' if event['type'] == 'note_on' else 'blue'
            plt.scatter(time_in_beats, event['note'], color=color, label='Original Note' if 'Original Note' not in plt.gca().get_legend_handles_labels()[1] else "")

        # Plot played MIDI notes
        for event in played_events:
            time_in_beats = event['time'] / self.ticks_per_beat
            color = 'orange' if event['type'] == 'note_on' else 'purple'
            plt.scatter(time_in_beats, event['note'], color=color, label='Played Note' if 'Played Note' not in plt.gca().get_legend_handles_labels()[1] else "")

        # Mark wrong notes
        for event in wrong_notes:
            time_in_beats = event['time'] / self.ticks_per_beat
            plt.scatter(time_in_beats, event['note'], color='red', label='Wrong Note' if 'Wrong Note' not in plt.gca().get_legend_handles_labels()[1] else "")

        # Final plot adjustments
        plt.title(f'MIDI Comparison (BPM={self.bpm})')
        plt.xlabel('Time (Beats)')
        plt.ylabel('MIDI Note Number')
        plt.grid(True)
        plt.legend()
        plt.show()

    def replay(self):
        """Replay mode: compares entire MIDI files."""
        original_events = self.parse_midi(self.original_midi)
        played_events = self.parse_midi(self.played_midi)
        wrong_notes = self.compare_notes(original_events, played_events)
        self.plot_midi(original_events, played_events, wrong_notes)

    def realtime(self):
        """Realtime mode: plays and compares notes in real time."""
        original_events = self.parse_midi(self.original_midi)
        played_events = []
        wrong_notes = []

        with mido.open_input() as inport:
            start_time = mido.time.time()
            for msg in inport:
                if msg.type in ['note_on', 'note_off']:
                    elapsed_time = (mido.time.time() - start_time) / self.seconds_per_tick
                    played_events.append({'time': elapsed_time, 'note': msg.note, 'type': msg.type, 'velocity': msg.velocity})

                    # Check if the note matches any in the original
                    if not any(
                        original['note'] == msg.note and msg.type == original['type']
                        for original in original_events
                    ):
                        wrong_notes.append({'time': elapsed_time, 'note': msg.note, 'type': msg.type, 'velocity': msg.velocity})

                    self.plot_midi(original_events, played_events, wrong_notes)

if __name__ == "__main__":
    # Initialize the comparer with the original and played MIDI files
    midifile = 'Piano Video/Twinkle Twinkle Little Star/Twinkle Twinkle Little Star BPM100 C5.mid'
    comparer = MIDIComparer(
        original_midi_path='Piano Video/Twinkle Twinkle Little Star/Twinkle Twinkle Little Star BPM100 C5.mid',
        played_midi_path='Piano Video/Twinkle Twinkle Little Star/Twinkle Twinkle Little Star BPM100 C5 test.mid',
        bpm=100
    )

    # Run replay mode or realtime mode
    # mode = input("Enter mode (replay/realtime): ").strip().lower()
    mode = 'replay'
    if mode == 'replay':
        comparer.replay()
    elif mode == 'realtime':
        comparer.realtime()
    else:
        print("Invalid mode. Please choose 'replay' or 'realtime'.")
