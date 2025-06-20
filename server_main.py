import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread, Event
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any

import torch
import queue
import time
from socketserver import ThreadingMixIn
import logging
from TTS.api import TTS
from multiprocessing import Manager, Process
from format_converters import convert_wav_to_mp3, create_timestamped_filename
from setuppers import ensure_config_files

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SERVER_HOST = 'localhost'
# SERVER_PORT = 8080

SPEAKER_DOMINUS = "pricelius_v2"
def get_available_speakers():
    """Get list of available speaker voices from speakers directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    speakers_dir = os.path.join(script_dir, "speakers")

    if not os.path.exists(speakers_dir):
        print("No path, z")
        return [SPEAKER_DOMINUS]  # Default

    speakers = [
        f.replace(".wav", "")
        for f in os.listdir(speakers_dir)
        if f.endswith(".wav")
    ]
    return speakers or [SPEAKER_DOMINUS]


class AIWorker:
    def startTTS(self, tts_index: int, device: str):
        with open('models.json', 'r') as filee:
            models = json.load(filee)
        print("Available models: ", models)

        tts = None
        tts = TTS(model_path=models[tts_index]["path"],
                          config_path=models[tts_index]["config"],
                          progress_bar=True).to(device)
        return tts

    def generateTextFromAudio(self, ttts, input_text: str, speaker: str, speed: float, file_path_o: str,
                              emotion: str = "Angry", gain: float=0.0):
        if speaker is None or not speaker in get_available_speakers():
            speaker = SPEAKER_DOMINUS
        ttts.tts_to_file(text=input_text, speaker_wav=f"speakers/{speaker}.wav", language="ru",
                         file_path=file_path_o, emotion="Angry", speed=speed)
        return convert_wav_to_mp3(file_path_o, gain=gain)

    def __init__(self, model_id):
        self.model_id = model_id
        self.device = 'cpu'
        self.model = self.startTTS(model_id, self.device)
        logger.info(f"AI Worker initialized using device: {self.device}")

    def process_task(self, task_data):
        try:
            out_name = create_timestamped_filename(f"output-{task_data['speaker']}", "wav")
            out = self.generateTextFromAudio(
                self.model,
                task_data["input_text"],
                task_data["speaker"],
                task_data["speed"],
                out_name,
                task_data["emotion"],
                task_data["gain"]
            )
            return {
                'output': out,
                'request_id': task_data.get('request_id', 'unknown'),
                'status': 'success'
            }
        except Exception as e:
            return {
                'error': str(e),
                'request_id': task_data.get('request_id', 'unknown'),
                'status': 'error'
            }


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class HTTPRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, task_queue, result_queue, *args, **kwargs):
        self.task_queue = task_queue
        self.result_queue = result_queue
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests for both speakers list and audio downloads"""
        if self.path == '/speakers.json':
            self.handle_speakers_list()
        elif self.path.startswith('/output/'):
            self.handle_audio_download()
        else:
            self.send_error(404, "Not Found")

    def handle_audio_download(self):
        """Serve generated audio files for download from output directory"""
        try:
            # Extract filename from path
            filename = os.path.basename(self.path)
            filepath = os.path.join('output', filename)

            # Security check - prevent directory traversal
            if not os.path.abspath(filepath).startswith(os.path.abspath('output')):
                self.send_error(403, "Forbidden")
                return

            if not os.path.exists(filepath):
                self.send_error(404, "File not found")
                return

            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(os.path.getsize(filepath)))
            self.end_headers()

            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())

        except Exception as e:
            self.send_error(500, f"Download error: {str(e)}")

    def handle_speakers_list(self):
        """Generate and send speakers.json response"""
        try:
            speakers = get_available_speakers()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "speakers": speakers,
                "default_speaker": SPEAKER_DOMINUS,
                "status": "success"
            }).encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            request_data = json.loads(post_data.decode('utf-8'))
            request_id = request_data.get('request_id', str(time.time()))

            if not all(k in request_data for k in ['input_text', 'speaker', 'speed', 'emotion', 'gain']):
                raise ValueError("Missing required fields in request")

            self.task_queue.put({
                'input_text': request_data['input_text'],
                'speaker': request_data['speaker'],
                'speed': request_data['speed'],
                'emotion': request_data['emotion'],
                'gain': request_data['gain'],
                'request_id': request_id
            })

            result = None
            while result is None or result.get('request_id') != request_id:
                try:
                    result = self.result_queue.get(timeout=1)
                    if result.get('request_id') != request_id:
                        self.result_queue.put(result)
                except queue.Empty:
                    continue

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_error(400, str(e))


def run_http_server(task_queue, result_queue, shutdown_event, host, port):
    logger.info(f"Starting HTTP server on {host}:{port}")

    def handler(*args, **kwargs):
        return HTTPRequestHandler(task_queue, result_queue, *args, **kwargs)

    server = ThreadedHTTPServer((host, port), handler)
    while not shutdown_event.is_set():
        server.handle_request()
    server.server_close()
    logger.info("HTTP server shut down")


def worker_process(model_id, task_queue, result_queue):
    """Worker function that runs in its own process"""
    worker = AIWorker(model_id)
    while True:
        try:
            task = task_queue.get()
            if task is None:  # Shutdown signal
                break
            result = worker.process_task(task)
            result_queue.put(result)
        except Exception as e:
            logger.error(f"Worker error: {e}")
            break


def main(kwargs: dict = None):
    with Manager() as manager:
        # Create process-safe queues
        task_queue = manager.Queue()
        result_queue = manager.Queue()
        shutdown_event = manager.Event()

        # Start HTTP server in main thread
        server_thread = Thread(
            target=run_http_server,
            args=(task_queue, result_queue, shutdown_event, kwargs["server_ip"], kwargs["server_port"]),
            daemon=True
        )
        server_thread.start()

        # Start worker processes
        num_workers = kwargs["workers_count"]
        workers = []
        for _ in range(num_workers):
            p = Process(
                target=worker_process,
                args=(kwargs["model_id"], task_queue, result_queue)
            )
            p.start()
            workers.append(p)

        try:
            while True:
                time.sleep(1)
                # Check if any workers died
                if any(not p.is_alive() for p in workers):
                    logger.error("A worker process died, restarting...")
                    dead = [p for p in workers if not p.is_alive()]
                    for p in dead:
                        workers.remove(p)
                        new_p = Process(
                            target=worker_process,
                            args=(kwargs["model_id"], task_queue, result_queue)
                        )
                        new_p.start()
                        workers.append(new_p)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            shutdown_event.set()

            # Signal workers to stop
            for _ in range(num_workers):
                task_queue.put(None)

            # Wait for workers
            for p in workers:
                p.join()

            server_thread.join()
            logger.info("All processes stopped")


if __name__ == '__main__':
    ensure_config_files()
    with open('config.json', 'r') as file:
        data = json.load(file)
    SPEAKER_DOMINUS = data["default_speaker"]
    main(kwargs=data)