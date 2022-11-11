import subprocess
from utils.transcriptor import Transcriptor

def get_config():
    import json
    with open('config.json') as f:
        config = json.load(f)
    return config

def list_all_videos():
    # Get the bucket name
    bucket_name = get_config()['bucket_videos']

    # List all videos in the bucket
    command = 'gsutil ls ' + bucket_name
    result = subprocess.check_output(command, shell=True)
    videos = result.decode('utf-8').split('\n')

    # Only keep video formats
    videos = [video for video in videos if video.endswith('.mp4') or video.endswith('.avi') or video.endswith('.mov')]
    return videos

def is_video_transcripted(video_uri):
    # Get the bucket name
    bucket_name = get_config()['bucket_transcripts']

    # Get the name of the transcription file
    transcription_file = video_uri.split('/')[-1].split('.')[0] + '.txt'

    # Check if the transcription file already exists in the bucket
    # Return True if it exists, False otherwise
    command = f'gsutil ls "{bucket_name}/{transcription_file}"'
    try:
        result = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as e:
        result = e.output
    return result.decode('utf-8') != ''

def main():
    # Get all videos
    videos = list_all_videos()

    # Instantiate the transcriptor
    transcriptor = Transcriptor()
    for video in videos:
        # Check if the video is already transcripted
        if is_video_transcripted(video):
            print(f'[INFO] {video} is already transcripted')
            continue
        # Convert the video file to audio file
        transcriptor.convert_video_uri_to_audio(video)
        # Transcribe the audio file
        transcriptor.transcribe_gcs()
        transcriptor.write_transcription_to_file()
        transcriptor.upload_transcription_to_gcs()
        transcriptor.delete_local_files()


if __name__ == '__main__':
    main()