import google.generativeai as genai
import time
import json
import ffmpeg
from typing import Dict, Any
import dotenv
from flask import Flask, request, jsonify
import boto3
import os
from PIL import Image

app = Flask(__name__)

def get_video_metadata(video_path: str) -> Dict[str, Any]:
    try:
        probe = ffmpeg.probe(video_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        duration = float(probe['format'].get('duration', 0))
        fps = eval(video_info.get('r_frame_rate', '0/1'))
        width = int(video_info.get('width', 0))
        height = int(video_info.get('height', 0))
        
        metadata = {
            "duration": duration,
            "fps": float(fps),
            "resolution": f"{width}x{height}"
        }
        return metadata
    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e}")
        return {}

def get_image_metadata(image_path: str) -> Dict[str, Any]:
    with Image.open(image_path) as img:
        metadata = {
            "resolution": f"{img.width}x{img.height}",
            "format": img.format
        }

def get_image_metadata(image_path: str) -> Dict[str, Any]:
    with Image.open(image_path) as img:
        metadata = {
            "resolution": f"{img.width}x{img.height}",
            "format": img.format
        }
    return metadata

def download_files_from_s3_folder(s3_folder_link: str, download_dir: str) -> None:
    s3 = boto3.client('s3')
    bucket_name, prefix = s3_folder_link.replace("s3://", "").split("/", 1)
    objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    if 'Contents' in objects:
        for obj in objects['Contents']:
            key = obj['Key']
            if key.endswith('/'):
                continue
            local_path = os.path.join(download_dir, os.path.basename(key))
            s3.download_file(bucket_name, key, local_path)

def generate_story(file_path: str, location: str, api_key: str, model_name: str = "gemini-1.5-pro") -> Dict[str, Any]:
    try:
        # Configure Gemini
        genai.configure(api_key="AIzaSyCD7egvvRfwRC7RY2SdZg_MIWK3IG_QeaU")
        model = genai.GenerativeModel(model_name)

        # Determine if the file is a video or an image
        if file_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            metadata = get_video_metadata(file_path)
            file_type = "video"
        elif file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
            metadata = get_image_metadata(file_path)
            file_type = "image"
        else:
            raise ValueError("Unsupported file type")

        # Upload and process file
        print(f"Uploading {file_type}...")
        uploaded_file = genai.upload_file(path=file_path)
        
        while uploaded_file.state.name == "PROCESSING":
            print('.', end='')
            time.sleep(10)
            uploaded_file = genai.get_file(uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise ValueError(f"{file_type.capitalize()} processing failed: {uploaded_file.state.name}")

        prompt = f"""You are an Expert {file_type.capitalize()}grapher that helps to storytell moments.
        1. Recognize the {file_type} and create a travel story about it.
        2. Script should be according to the length of the {file_type}: {metadata.get('duration', 'N/A')} seconds. Keep it short so it can be added to the {file_type}.
        3. Location: {location}
        4. Return response in JSON format with keys: story_text, duration_seconds, recommended_voice_tone
        """

        print("\nGenerating Content...")
        response = model.generate_content(
            [uploaded_file, prompt],
            request_options={"timeout": 600}
        )
        try:
            story_content = json.loads(response.text)
        except json.JSONDecodeError:
            story_content = {
                "story_text": response.text,
                "duration_seconds": metadata.get("duration", "N/A"),
                "recommended_voice_tone": "neutral"
            }

        result = {
            "metadata": metadata,
            "location": location,
            "story": story_content,
            "status": "success"
        }

        return result

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "metadata": metadata if 'metadata' in locals() else None
        }

@app.route('/generate_story', methods=['POST'])
def generate_story_endpoint():
    data = request.json
    s3_folder_link = data.get('s3_folder_link')
    location = data.get('location')
    api_key = "AIzaSyCD7egvvRfwRC7RY2SdZg_MIWK3IG_QeaU"

    if not s3_folder_link or not location:
        return jsonify({"status": "error", "error_message": "s3_folder_link and location are required"}), 400

    download_dir = "downloaded_files"
    os.makedirs(download_dir, exist_ok=True)
    download_files_from_s3_folder(s3_folder_link, download_dir)

    results = []
    for file_name in os.listdir(download_dir):
        file_path = os.path.join(download_dir, file_name)
        result = generate_story(
            file_path=file_path,
            location=location,
            api_key=api_key
        )
        results.append(result)
        os.remove(file_path)  

    os.rmdir(download_dir)

    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(debug=True)