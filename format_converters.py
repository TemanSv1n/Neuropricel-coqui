from pydub import AudioSegment
import os
from ffmpeg import ffmpeg
import os
from datetime import datetime

from pydub import AudioSegment
ffmpeg_string = r"binaries\ffmpeg"
if os.name == "nt":
    ffmpeg_string = r"binaries\ffmpeg.exe"
AudioSegment.converter = ffmpeg_string


def amplify_volume(input_path, output_path=None, gain_db=3.0, delete_original=False):
    try:
        # Load the audio file
        audio = AudioSegment.from_file(input_path)
        # Apply gain (amplification)
        louder_audio = audio + gain_db
        # Determine output path
        if output_path is None:
            output_path = input_path
        # Export the amplified audio
        louder_audio.export(output_path, format="mp3")
        # Clean up if requested
        if delete_original and output_path != input_path:
            os.remove(input_path)

        return output_path

    except Exception as e:
        print(f"Error during volume amplification: {str(e)}")
        return False

def resample(path):
    try:
        # Load the audio file
        audio = AudioSegment.from_mp3(path)

        # Get the current frame rate
        original_frame_rate = audio.frame_rate
        # Resample to 48000 Hz
        audio = audio.set_frame_rate(48000)

        # Export the resampled audio, overwriting the original file
        audio.export(path, format="mp3")

        return True
    except Exception as e:
        print(f"Error during resampling: {str(e)}")
        return False


def mono_to_stereo(input_path, output_path=None, delete_original=False):
    try:
        audio = AudioSegment.from_file(input_path)

        if audio.channels == 2:
            return input_path

        # Simple method - pydub handles the channel duplication
        stereo_audio = audio.set_channels(2)

        if output_path is None:
            output_path = input_path

        stereo_audio.export(output_path, format="mp3")

        if delete_original and output_path != input_path:
            os.remove(input_path)

        return output_path

    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def convert_wav_to_mp3(input_path, output_path=None, delete_original=True, gain: float=0.0):
    try:
        audio = AudioSegment.from_wav(input_path)
        if output_path is None:
            output_path = os.path.splitext(input_path)[0] + ".mp3"
        audio.export(output_path, format="mp3")

        if (delete_original):
            os.remove(input_path)

        resample(output_path)
        amplify_volume(output_path, gain_db=gain)
        mono_to_stereo(output_path)
        return output_path

    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        return False


def create_timestamped_filename(prefix, file_ext, folder="output"):
    os.makedirs(folder, exist_ok=True)  # Create folder if needed

    # Human-readable timestamp (YYYY-MM-DD_HH-MM-SS)
    timestamp = datetime.now().strftime("%Y-%d-%m_%H-%M-%S")

    # Try the simple filename first
    filename = f"{prefix}_{timestamp}.{file_ext}"
    full_path = os.path.join(folder, filename)

    # If exists, add incrementing number
    counter = 1
    while os.path.exists(full_path):
        filename = f"{prefix}_{timestamp}_{counter}.{file_ext}"
        full_path = os.path.join(folder, filename)
        counter += 1

    return full_path


# Example usage
if __name__ == "__main__":
    input_file = "test.wav"

    # Convert and delete original
    convert_wav_to_mp3(input_file, delete_original=True)