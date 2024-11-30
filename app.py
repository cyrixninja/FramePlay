import logging
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import zipfile
import tempfile
import shutil
import requests
import os
import cv2
from flask import Flask, render_template, request, redirect, url_for
import time
# Load environment variables
load_dotenv()
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024  # 256MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'zip', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov'}

# Get environment variables with error handling
S3_BUCKET = os.getenv('AWS_BUCKET')  
S3_VID_BUCKET = os.getenv('S3_VID_BUCKET')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
KESTRA_URL = os.getenv('KESTRA_URL')
KESTRA_USERNAME = os.getenv('KESTRA_USERNAME')
KESTRA_PASSWORD = os.getenv('KESTRA_PASSWORD')

# Validate required environment variables
if not all([S3_BUCKET, AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION, KESTRA_URL, KESTRA_USERNAME, KESTRA_PASSWORD]):
    missing = []
    if not S3_BUCKET: missing.append('AWS_BUCKET')
    if not AWS_ACCESS_KEY: missing.append('AWS_ACCESS_KEY_ID')
    if not AWS_SECRET_KEY: missing.append('AWS_SECRET_ACCESS_KEY') 
    if not AWS_REGION: missing.append('AWS_REGION')
    if not KESTRA_URL: missing.append('KESTRA_URL')
    if not KESTRA_USERNAME: missing.append('KESTRA_USERNAME')
    if not KESTRA_PASSWORD: missing.append('KESTRA_PASSWORD')
    logging.error(f"Missing required environment variables: {', '.join(missing)}")
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

def upload_to_s3(file_path, bucket, object_name=None):
    """Upload a file to S3 bucket"""
    if object_name is None:
        object_name = 'video.mp4'

    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION
    )

    try:
        s3_client.upload_file(file_path, bucket, object_name)
        return True
    except ClientError as e:
        logging.error(f"S3 upload error: {e}")
        return False
    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def wait_for_kestra_workflow(execution_id):
    """Poll the Kestra workflow status until it completes."""
    while True:
        response = requests.get(
            f"{KESTRA_URL}/api/v1/executions/{execution_id}",
            auth=(KESTRA_USERNAME, KESTRA_PASSWORD)
        )
        if response.status_code != 200:
            logging.error(f"Failed to get Kestra workflow status: {response.text}")
            return False

        status = response.json()
        current_status = status.get('state', {}).get('current')
        logging.info(f"Kestra workflow status: {status}")

        if current_status in ['SUCCESS', 'WARNING']:
            return current_status == 'SUCCESS'

        time.sleep(10)  # Wait for 5 seconds before polling again

@app.route('/')
def index():
    return render_template('index.html')

def extract_frames_from_video(video_path, target_fps=30):
    """Extract frames from a video at a higher FPS for smoother output."""
    frames = []
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        logging.error(f"Could not open video file: {video_path}")
        return frames

    video_fps = cap.get(cv2.CAP_PROP_FPS) or target_fps
    frame_interval = max(1, round(video_fps / target_fps))
    frame_count = 0

    logging.info(f"Extracting frames from {video_path} at {target_fps} FPS")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            frames.append(frame)
        frame_count += 1

    cap.release()
    logging.info(f"Extracted {len(frames)} frames from {video_path}")
    return frames

def create_video_from_mixed_sources(image_files, video_files, output_path, fps=30):
    """Create video from both image files and video files."""
    if not image_files and not video_files:
        logging.error("No image or video files provided")
        return False

    all_frames = []
    logging.info(f"Processing {len(video_files)} videos and {len(image_files)} images")

    # Process video files
    for video_file in video_files:
        video_frames = extract_frames_from_video(video_file, fps)
        if video_frames:
            all_frames.extend(video_frames)

    # Resize all frames to a consistent resolution
    if all_frames:
        standard_height, standard_width = all_frames[0].shape[:2]

    # Process image files
    frames_per_image = fps * 5 
    for image_file in image_files:
        frame = cv2.imread(image_file)
        if frame is None:
            logging.warning(f"Could not read image file: {image_file}")
            continue
        # Resize images to match the standard resolution
        if all_frames:
            frame = cv2.resize(frame, (standard_width, standard_height))
        all_frames.extend([frame] * frames_per_image)
        logging.info(f"Added {frames_per_image} frames from image {image_file}")

    if not all_frames:
        logging.error("No valid frames found")
        return False

    # Write video
    try:
        height, width = standard_height, standard_width
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not video.isOpened():
            logging.error("Failed to create video writer")
            return False

        total_frames = len(all_frames)
        logging.info(f"Writing {total_frames} frames to {output_path}")

        for i, frame in enumerate(all_frames):
            video.write(frame)
            if i % 100 == 0:  # Log progress
                logging.info(f"Written {i}/{total_frames} frames")

        video.release()
        logging.info(f"Video creation completed: {output_path}")
        return True

    except Exception as e:
        logging.error(f"Error creating video: {e}")
        return False
@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        if 'media-upload' not in request.files:
            logging.error("No media-upload in request.files")
            return 'No file uploaded', 400
        
        files = request.files.getlist('media-upload')
        upload_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
        temp_dir = tempfile.mkdtemp()
        location = request.form.get('location')
        logging.info(f"Location: {location}")
        image_files = []
        video_files = []
        
        try:
            for file in files:
                if file and allowed_file(file.filename):
                    filename = os.path.join(upload_path, file.filename)
                    logging.info(f"Processing file: {filename}")
                    file.save(filename)
                    
                    if filename.endswith('.zip'):
                        with zipfile.ZipFile(filename, 'r') as zip_ref:
                            zip_ref.extractall(temp_dir)
                            for root, _, files in os.walk(temp_dir):
                                for f in files:
                                    filepath = os.path.join(root, f)
                                    ext = f.lower().split('.')[-1]
                                    logging.info(f"Found file in zip: {f} with extension {ext}")
                                    
                                    if ext in {'png', 'jpg', 'jpeg', 'gif'}:
                                        logging.info(f"Adding image file: {filepath}")
                                        image_files.append(filepath)
                                    elif ext in {'mp4', 'avi', 'mov'}:
                                        logging.info(f"Adding video file: {filepath}")
                                        video_files.append(filepath)
            
            logging.info(f"Found {len(image_files)} images and {len(video_files)} videos")
            
            if image_files or video_files:
                output_video = os.path.join(upload_path, 'output.mp4')
                if create_video_from_mixed_sources(image_files, video_files, output_video, 10):
                    logging.info("Video created successfully")
                    # Upload to S3
                    if upload_to_s3(output_video, S3_BUCKET):
                        logging.info("Video uploaded to S3 successfully")
                    else:
                        logging.error("Failed to upload video to S3")
                    
                    # Call Kestra workflow
                    kestra_payload = location
                    kestra_response = requests.post(
                        f"{KESTRA_URL}/api/v1/executions/webhook/frameflow/frameflow_process/frameplay",
                        json=kestra_payload,
                        auth=(KESTRA_USERNAME, KESTRA_PASSWORD)
                    )

                    if kestra_response.status_code == 200:
                        logging.info("Kestra workflow started successfully")
                        execution_id = kestra_response.json().get('id')
                        if wait_for_kestra_workflow(execution_id):
                            logging.info("Kestra workflow completed successfully")
                            video_url = S3_VID_BUCKET
                            return render_template('create.html', video_url=video_url)
                        else:
                            logging.error("Kestra workflow completed successfully")
                            video_url = S3_VID_BUCKET
                            return render_template('create.html', video_url=video_url)
                    else:
                        logging.error(f"Failed to start Kestra workflow: {kestra_response.text}")
                else:
                    logging.error("Failed to create video")
                    
        except Exception as e:
            logging.error(f"Error processing files: {str(e)}")
            return str(e), 500
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        
        return redirect(url_for('create'))
    
    return render_template('create.html')

@app.route('/working')
def working():
    return render_template('working.html')

if __name__ == '__main__':
    app.run(debug=True)