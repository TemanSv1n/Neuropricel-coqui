import requests
import json
import time
import os

# Server configuration
SERVER_URL = "http://localhost:8080"
REQUEST_TIMEOUT = 60  # seconds

DIRS = {
        'downloads':"downloads"
    }


def send_tts_request(text, speaker="pricelius_v2", speed=1.0, emotion="Angry", gain: float = 0.0):
    """
    Send a TTS request to the server and return the output file path

    Args:
        text (str): Text to convert to speech
        speaker (str): Speaker voice to use (default: "pricelius_v2")
        speed (float): Speech speed (default: 1.0)
        emotion (str): Emotion style (default: "Angry")

    Returns:
        str: Path to the generated audio file
    """
    payload = {
        "input_text": text,
        "speaker": speaker,
        "speed": speed,
        "emotion": emotion,
        "gain": gain,
        "request_id": str(int(time.time()))  # Unique request ID
    }

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(
            SERVER_URL,
            data=json.dumps(payload),
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        result = response.json()

        if result.get('status') == 'success':
            print(f"Successfully generated audio: {result['output']}")
            return result['output']
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

if __name__ == "__main__":
    for name, path in DIRS.items():
        os.makedirs(path, exist_ok=True)
        print(f"Ensured directory exists: {path}")
    # Example usage
    # print("Available speakers:\n")
    # count = 0
    # for i in get_available_speakers():
    #     print(f"{count} --- {i}")
    #     count+=1

    response = requests.get("http://localhost:8080/speakers.json")
    speakers = response.json()
    print("Available speakers:", speakers)

    # Customize these values
    selected_speaker = speakers["speakers"][int(input("Enter speaker number "))]
    text_to_speak = input("Enter Text ")

    speech_speed = 0.3
    emotion_style = "Angry"  # "Angry", "Happy", "Neutral"
    gain = 13

    # Send request
    audio_file = send_tts_request(
        text=text_to_speak,
        speaker=selected_speaker,
        speed=speech_speed,
        emotion=emotion_style,
        gain = gain
    )

    if audio_file:
        filename = os.path.basename(audio_file)  # Extract filename
        print("filename",filename)
        audio_response = requests.get(f"{SERVER_URL}/output/{filename}")
        print(f"{SERVER_URL}/output/{filename}")
        print("aresp",audio_response)

        #Save to current directory
        filename = os.path.join("downloads",filename)
        with open(filename, 'wb') as f:
            f.write(audio_response.content)

        print(f"Success! File saved as: {os.path.abspath(filename)}")
        if os.name == "nt":
            os.startfile(os.path.abspath(filename))