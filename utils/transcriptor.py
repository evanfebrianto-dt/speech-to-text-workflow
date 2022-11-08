# This is class for transcribing video files in google cloud storage into text
import os
import subprocess
import math
from utils.util import timeit

class Transcriptor:
    def __init__(self):
        # Get configuration from config.json
        def get_config():
            import json
            with open('config.json') as f:
                config = json.load(f)
            return config
        self.config = get_config()
        self.gcs_uri = None
        self.local_file = {}
        self.audio_length = None
        self.response = None

    # Convert the video file to audio file
    @timeit
    def convert_video_uri_to_audio(self, video_uri):
        # Get the audio file name
        self.local_file["audio_file"] = video_uri.split('/')[-1].split('.')[0] + '.flac'

        # Get the name of the video file locally
        self.local_file['video_file'] = video_uri.split('/')[-1]

        # Check if the video file exists locally
        if not os.path.exists(self.local_file['video_file']):
            # Download the video file locally
            command = f'gsutil cp "{video_uri}" .'
            subprocess.call(command, shell=True)
    
        print(f'[INFO] Downloaded {self.local_file["video_file"]} locally')

        # Check if the audio file already exists
        if os.path.exists(self.local_file["audio_file"]):
            print(f'[INFO] {self.local_file["audio_file"]} already exists locally')
        else:
            print(f'[INFO] Converting {self.local_file["video_file"]} to {self.local_file["audio_file"]}')
            # Convert the video file to audio file
            command = f'ffmpeg -i "{self.local_file["video_file"]}" -ac 1 -ar 16000 "{self.local_file["audio_file"]}"'
            subprocess.call(command, shell=True)
            print(f'[INFO] audio file {self.local_file["audio_file"]} created')

        # Check audio length
        command = f'ffprobe -i "{self.local_file["audio_file"]}" -show_entries format=duration -v quiet -of csv="p=0"'
        result = subprocess.check_output(command, shell=True)
        self.audio_length = float(result.decode('utf-8'))
        print(f'[INFO] Audio length: {self.audio_length}')

        # Upload the audio file to google cloud storage
        self.upload_audio_to_gcs(self.local_file["audio_file"])


    # Upload the audio file to google cloud storage
    @timeit
    def upload_audio_to_gcs(self, audio_file):
        # Get the bucket name
        bucket_name = self.config['bucket_audios']

        # Check if the audio file already exists in the bucket
        command = f'gsutil ls "{bucket_name}/{audio_file}"'
        result = subprocess.check_output(command, shell=True)
        if result.decode('utf-8') == '':
            # Upload the audio file to the bucket
            command = f'gsutil cp "{audio_file}" "{bucket_name}"'
            subprocess.call(command, shell=True)
            print(f'[INFO] {audio_file} uploaded to {bucket_name}')
        else:
            print(f'[INFO] {audio_file} already exists in {bucket_name}')
        
        # Get the gcs_uri
        self.gcs_uri = bucket_name + '/' + audio_file


    # Transcribe the audio file
    @timeit
    def transcribe_gcs(self, timeout_buffer=10):
        # Get the transcription file name
        self.local_file["transcription_file"] = self.gcs_uri.split('/')[-1].split('.')[0] + '.txt'

        # Check if the transcription file already exists locally
        if os.path.exists(self.local_file["transcription_file"]):
            print(f'[INFO] Skipping transcription because {self.local_file["transcription_file"]} already exists locally')
        else:
            """Asynchronously transcribes the audio file specified by the gcs_uri."""
            from google.cloud import speech

            client = speech.SpeechClient()

            audio = speech.RecognitionAudio(uri=self.gcs_uri)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
                sample_rate_hertz=16000,
                language_code="en-US",
            )

            operation = client.long_running_recognize(config=config, audio=audio)

            print(f'[INFO] Starting transcription for {self.gcs_uri}')
            self.response = operation.result(timeout=math.ceil(self.audio_length) + timeout_buffer)
            print(f'[INFO] Transcription completed')


    # Get the transcription
    def get_transcription(self):
        # Each result is for a consecutive portion of the audio. Iterate through
        # them to get the transcripts for the entire audio file.
        if self.response:
            for result in self.response.results:
                # The first alternative is the most likely one for this portion.
                print(u"Transcript: {}".format(result.alternatives[0].transcript))
                print("Confidence: {}".format(result.alternatives[0].confidence))
        else:
            print('[INFO] No transcription available')

    # Get the transcription and save it to a file
    @timeit
    def write_transcription_to_file(self):
        # Get the transcription file name
        self.local_file["transcription_file"] = self.gcs_uri.split('/')[-1].split('.')[0] + '.txt'

        # Check if the transcription file already exists locally
        if os.path.exists(self.local_file["transcription_file"]):
            print(f'[INFO] {self.local_file["transcription_file"]} already exists locally')
        else:
            # Get the transcription
            transcription = ''
            for result in self.response.results:
                # The first alternative is the most likely one for this portion.
                transcription += result.alternatives[0].transcript + '\n'

            # Write the transcription to a file
            with open(self.local_file["transcription_file"], 'w') as f:
                f.write(transcription)
                print(f'[INFO] {self.local_file["transcription_file"]} created locally')
    
    
    # Upload transcription result from self.response.result to google cloud storage
    @timeit
    def upload_transcription_to_gcs(self):
        # Get the bucket name
        bucket_name = self.config['bucket_transcripts']

        # Get the transcription file name
        transcription_file = self.gcs_uri.split('/')[-1].split('.')[0] + '.txt'

        # Check if the transcription file already exists in the bucket
        command = f'gsutil ls "{bucket_name}/{transcription_file}"'

        # If it does not exist, gsutil will return CommandException: One or more URLs matched no objects.
        try:
            result = subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError as e:
            result = e.output

        if result.decode('utf-8') == '':
            # Upload the transcription file to the bucket
            command = f'gsutil cp "{self.local_file["transcription_file"]}" "{bucket_name}"'
            subprocess.call(command, shell=True)
            print(f'[INFO] {self.local_file["transcription_file"]} uploaded to {bucket_name}')


    # Delete the local files
    @timeit
    def delete_local_files(self):
        for file in self.local_file.values():
            if os.path.exists(file):
                os.remove(file)
                print(f'[INFO] {file} deleted locally')