## Info section
Coqui TTS + XTTS AI voice generator. Works with HTTP requests. Requesting example can be found in /client/client_test_goonner.py. \
Works with queue of requests.

## Requirements
**PYTHON 3.11**, \
requirements.txt, \
ffmpeg binary in /binaries/ folder

Voice model should be placed into /models/"model_name"/. By default its XTTS_v2, could be found on huggingface.\
Edit path to model is possible in models.json

config.json:
````json
"model_id": 0, model index from models.json
  "workers_count": 1, count of parallel working processes
  "server_ip": "0.0.0.0",
  "server_port": 8080,
  "default_speaker": "pricelius_v2"
````
