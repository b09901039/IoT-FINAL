import time
import cv2
from picamera2 import Picamera2
from flask import Flask, Response

class CameraStream:
    def __init__(self, resolution=(640, 480), framerate=60):
        self.camera = Picamera2()
        self.resolution = resolution
        self.framerate = framerate
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

            # Encode the frame as JPEG
            _, jpeg_frame = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_frame.tobytes() + b'\r\n')

            # Calculate FPS
            self.frame_count += 1
            elapsed_time = time.time() - self.start_time
            if elapsed_time >= 1.0:  # Every second
                fps = self.frame_count / elapsed_time
                print(f"FPS: {fps:.2f}")
                self.frame_count = 0
                self.start_time = time.time()

class CameraApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.camera_stream = CameraStream()

        # Setup routes for the Flask app
        self.app.add_url_rule('/video_feed', 'video_feed', self.video_feed)

    def video_feed(self):
        return Response(self.camera_stream.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def run(self):
        try:
            self.camera_stream.start()  # Start the camera
            self.app.run(host='0.0.0.0', port=5000, threaded=True)
        except KeyboardInterrupt:
            self.camera_stream.stop()  # Stop the camera when interrupted

if __name__ == '__main__':
    camera_app = CameraApp()
    camera_app.run()
