import cv2
import requests
import time
import numpy as np
import os
from datetime import datetime

from flask import Flask, Response

app = Flask(__name__)
@app.route('/video_feed')
def video_feed():
	return Response(main(), mimetype='multipart/x-mixed-replace; boundary=frame')


def main():
	IP = '192.168.126.100'
	stream_url = f"http://{IP}:5000/video_feed"

	# Open a connection to the video stream
	# cap = cv2.VideoCapture(stream_url)
	stream = requests.get(stream_url, stream=True)
	if stream.status_code != 200:
		print(f"Failed to connect to the stream. Status code: {stream.status_code}")
		exit()

	fps = 0
	frame_count = 0
	start_time = time.time()


	# Variables for video recording
	is_recording = False
	fps_video = 30
	frame_width = 640
	frame_height = 480

	fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
	# fourcc = cv2.VideoWriter_fourcc('H', '2', '6', '4')
	# fourcc = cv2.VideoWriter_fourcc(*'XVID')
	out = None
	# out = cv2.VideoWriter(output_filename, fourcc, fps_video, (frame_width, frame_height))
	motion_blur_time = None

	def calculate_blur(frame):
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		laplacian = cv2.Laplacian(gray, cv2.CV_64F)
		variance = laplacian.var()		
		return variance

	def detect_motion_blur(frame, threshold=200):
		blur_score = calculate_blur(frame)
		# print(blur_score)
		if blur_score < threshold:
			return True 
		else:
			return False

	try:
		byte_buffer = b''

		for chunk in stream.iter_content(chunk_size=1024):
			byte_buffer += chunk

			# Find frame boundaries in the buffer
			start_index = byte_buffer.find(b'\xff\xd8')  # JPEG start marker
			end_index = byte_buffer.find(b'\xff\xd9')   # JPEG end marker

			if start_index != -1 and end_index != -1:
				# Extract frame from buffer
				jpg_frame = byte_buffer[start_index:end_index+2]
				byte_buffer = byte_buffer[end_index+2:]

				try:
					frame = cv2.imdecode(np.frombuffer(jpg_frame, np.uint8), cv2.IMREAD_COLOR)
				except Exception as e:
					print(f"Failed to decode frame: {e}")
					continue
		
				if frame is not None:
					frame = cv2.rotate(frame, cv2.ROTATE_180)
					frame = cv2.flip(frame, 1)

					fps_text = f"{fps:3.0f} FPS"
					cv2.putText(frame, fps_text, (frame_width - 80, 20), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 0), 2, cv2.LINE_AA)

					# cv2.putText(frame, "Recording...", (frame_width - 108, 40), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 255), 2, cv2.LINE_AA)
					# cv2.putText(frame, "Video unstable", (frame_width//2-30, 40), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 255), 2, cv2.LINE_AA)

					if detect_motion_blur(frame):						
						motion_blur_time = time.time()
					if motion_blur_time is not None and time.time() - motion_blur_time < 1.0:
						cv2.putText(frame, "Motion blur detected!", (frame_width//2-0, 40), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 255), 2, cv2.LINE_AA)
						# print("Motion blur detected!")
					else:
						motion_blur_time = None 


					if is_recording:
						cv2.putText(frame, "Recording...", (frame_width - 110, 40), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 255), 2, cv2.LINE_AA)
						if out is None:
							current_datetime = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
							output_filename = f"output {current_datetime}.mp4"
							out = cv2.VideoWriter(output_filename, fourcc, fps_video, (frame_width, frame_height))
                        
						out.write(frame)	


					elapsed_time = time.time() - start_time
					if elapsed_time >= 1.0:
						# fps = frame_count / elapsed_time
						fps = int(frame_count)

						# print(f"FPS: {fps:.2f}")
						frame_count = 0
						start_time = time.time()

					_, jpeg_frame = cv2.imencode('.jpg', frame)
					yield (b'--frame\r\n'
						b'Content-Type: image/jpeg\r\n\r\n' + jpeg_frame.tobytes() + b'\r\n')


					cv2.imshow('Video Stream', frame)
					frame_count += 1

					key = cv2.waitKey(1) & 0xFF
					if key == ord('q'):
						break
					elif key == ord('r'): 
						is_recording = not is_recording
						if not is_recording and out is not None:
							print("Recording stopped...")
							out.release()
							out = None
						elif is_recording:
							print("Recording started...")

	except KeyboardInterrupt:
		print("Interrupted by user. Closing...")
	except Exception as e:
		print(f"An error occurred: {e}")

	finally:
		cv2.destroyAllWindows()


if __name__=="__main__":
	# main()
	app.run(host='0.0.0.0', port=1234, threaded=True)