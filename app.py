import google.generativeai as genai
import time
import json
from flask import Flask, request, jsonify
import boto3
import os

app = Flask(__name__)

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

def generate_story(file_path: str, location: str, api_key: str, model_name: str = "gemini-1.5-pro"):
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        # Determine file type
        file_type = "video" if file_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')) else "image"

        # Upload and process file
        print(f"Uploading {file_type}...")
        uploaded_file = genai.upload_file(path=file_path)
        
        while uploaded_file.state.name == "PROCESSING":
            print('.', end='')
            time.sleep(10)
            uploaded_file = genai.get_file(uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise ValueError(f"{file_type.capitalize()} processing failed")

        prompt = f"""You are an Expert {file_type.capitalize()}grapher that helps to storytell moments.
        1. Recognize the {file_type} and create a travel story about it.
        2. Location: {location}
        3. Return response in JSON format with keys: story_text, recommended_voice_tone
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
                "recommended_voice_tone": "neutral"
            }

        return {
            "location": location,
            "story": story_content,
            "status": "success"
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }

@app.route('/generate_story', methods=['POST'])
def generate_story_endpoint():
    try:
        data = request.json
        s3_folder_link = data.get('s3_folder_link')
        location = data.get('location')
        api_key = ""

        if not s3_folder_link or not location:
            return jsonify({
                "status": "error", 
                "error_message": "s3_folder_link and location are required"
            }), 400

        download_dir = "downloaded_files"
        os.makedirs(download_dir, exist_ok=True)

        try:
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

            return jsonify({
                "status": "success",
                "results": results
            })

        finally:
            # Cleanup downloaded files
            import shutil
            if os.path.exists(download_dir):
                shutil.rmtree(download_dir)

    except Exception as e:
        return jsonify({
            "status": "error",
            "error_message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)