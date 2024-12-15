import mido
import matplotlib.pyplot as plt

def main():
	# Set the BPM (Beats per Minute)
	bpm = 100
	ticks_per_beat = 480  # Usually the default ticks per beat in MIDI files (could be different depending on your file)

	# Read the MIDI file
	midi_file = mido.MidiFile('Piano Video/Twinkle Twinkle Little Star/Twinkle Twinkle Little Star BPM100 C5.mid')

	# Initialize plot
	plt.figure(figsize=(12, 6))

	# BPM to beats per second conversion
	seconds_per_beat = 60 / bpm
	ticks_per_beat = midi_file.ticks_per_beat

	# Plot each message
	for track in midi_file.tracks:
		time = 0  # Time in ticks
		for msg in track:
			time += msg.time  # Accumulate the time in ticks
			time_in_beats = time / ticks_per_beat  # Convert ticks to beats

			# Plotting Note On and Note Off events
			if msg.type == 'note_on' and msg.velocity > 0:
				plt.scatter(time_in_beats, msg.note, color='green', label='Note On' if 'Note On' not in plt.gca().get_legend_handles_labels()[1] else "")
			elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
				plt.scatter(time_in_beats, msg.note, color='red', label='Note Off' if 'Note Off' not in plt.gca().get_legend_handles_labels()[1] else "")

	# Adjust x-axis to show detailed time in beats
	plt.title(f'MIDI Event Timeline (BPM={bpm})')
	plt.xlabel('Time (Beats)')
	plt.ylabel('MIDI Note Number')
	
	# Adjust x-axis ticks to show finer granularity
	plt.xticks(range(0, int(time_in_beats) + 1))  # Set x-ticks to range from 0 to max beats
	plt.grid(True)

	# Show the plot
	plt.legend()
	plt.show()

if __name__ == "__main__":
	main()
	