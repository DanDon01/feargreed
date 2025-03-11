import os
import time
from PIL import Image
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil

class GifHandler(FileSystemEventHandler):
    def __init__(self, input_folder, output_folder):
        self.input_folder = input_folder
        self.output_folder = output_folder

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith('.gif'):
            self.process_gif(event.src_path)

    def process_gif(self, gif_path):
        try:
            # Create unique folder name based on timestamp
            timestamp = int(time.time())
            gif_name = os.path.splitext(os.path.basename(gif_path))[0]
            output_dir = os.path.join(self.output_folder, f"{gif_name}_{timestamp}")
            os.makedirs(output_dir, exist_ok=True)

            # Open and split the GIF
            with Image.open(gif_path) as gif:
                for frame in range(gif.n_frames):
                    gif.seek(frame)
                    frame_img = gif.convert('RGBA')
                    frame_img.save(os.path.join(output_dir, f'frame_{frame:03d}.png'))

            # Move original GIF to processed folder
            processed_folder = os.path.join(self.input_folder, 'processed')
            os.makedirs(processed_folder, exist_ok=True)
            shutil.move(gif_path, os.path.join(processed_folder, os.path.basename(gif_path)))

        except Exception as e:
            print(f"Error processing {gif_path}: {str(e)}")

def start_monitoring(input_folder='gifs/incoming', output_folder='gifs/animations'):
    # Create folders if they don't exist
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    event_handler = GifHandler(input_folder, output_folder)
    observer = Observer()
    observer.schedule(event_handler, input_folder, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_monitoring()
