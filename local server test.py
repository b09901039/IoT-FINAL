import cv2
import requests
from threading import Thread

class StreamViewer:
    def __init__(self, stream_url):
        self.stream_url = stream_url
        self.is_running = True
        self.capture_thread = None

    def start(self):
        self.is_running = True
        self.capture_thread = Thread(target=self._capture_stream)
        self.capture_thread.start()

    def stop(self):
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join()

    def _capture_stream(self):
        cap = cv2.VideoCapture(self.stream_url)
        while True:
            success, frame = cap.read()
            if not success:
                print("Failed to read from stream. Retrying...")
                break

            # Display the frame in a window
            cv2.imshow('Stream Viewer', frame)

            # Break on pressing the ESC key
            if cv2.waitKey(1) == 27:
                self.stop()
                break

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    stream_url = "http://192.168.188.100:5000/video"  # Adjust the URL as needed
    viewer = StreamViewer(stream_url)

    try:
        viewer.start()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        viewer.stop()
