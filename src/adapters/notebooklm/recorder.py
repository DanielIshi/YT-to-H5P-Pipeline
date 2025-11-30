
import os
import time
import json
from datetime import datetime
from mss import mss
import numpy as np
import cv2
from PIL import Image

class Recorder:
    def __init__(self, output_dir="output/recordings"):
        self.output_dir = output_dir
        self.frames_dir = os.path.join(output_dir, "frames")
        os.makedirs(self.frames_dir, exist_ok=True)
        self.timeline = []
        self.is_recording = False
        self.start_time = None

    def start(self):
        self.is_recording = True
        self.start_time = time.time()
        self.timeline = []

    def stop(self):
        self.is_recording = False
        timeline_path = os.path.join(self.output_dir, f"timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(timeline_path, "w") as f:
            json.dump(self.timeline, f, indent=4)
        print(f"Timeline saved to {timeline_path}")

    def capture_frame(self, description=""):
        if not self.is_recording:
            return

        timestamp = time.time() - self.start_time
        frame_filename = f"frame_{len(self.timeline):04d}.png"
        frame_path = os.path.join(self.frames_dir, frame_filename)

        with mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(frame_path)

        self.timeline.append({
            "timestamp": timestamp,
            "image": frame_path,
            "description": description
        })

    def create_video(self, video_filename="animation.mp4", fps=24):
        video_path = os.path.join(self.output_dir, video_filename)
        
        if not self.timeline:
            print("No frames to create a video.")
            return

        # Get frame size from the first image
        first_frame_path = self.timeline[0]['image']
        first_frame = cv2.imread(first_frame_path)
        if first_frame is None:
            print(f"Error reading first frame: {first_frame_path}")
            return
        height, width, layers = first_frame.shape

        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

        if not video.isOpened():
            print(f"Error: Video writer could not be opened for path: {video_path}")
            return

        for frame_info in self.timeline:
            frame_path = frame_info['image']
            frame = cv2.imread(frame_path)
            if frame is not None:
                video.write(frame)
            else:
                print(f"Warning: Could not read frame {frame_path}")

        video.release()
        print(f"Video saved to {video_path}")

if __name__ == '__main__':
    recorder = Recorder()
    recorder.start()
    recorder.capture_frame("First frame")
    time.sleep(1)
    recorder.capture_frame("Second frame")
    recorder.stop()
    recorder.create_video(fps=1)
