import google.generativeai as genai
import time
import json
import cv2
from typing import Dict, Any, Optional
import dotenv

def get_video_metadata(video_path: str) -> Dict[str, Any]:
    cap = cv2.VideoCapture(video_path)
    metadata = {
        "duration": float(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)),
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
        "resolution": f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
    }
    cap.release()
    return metadata

def generate_video_story(
    video_path: str,
    location: str,
    api_key: str,
    model_name: str = "gemini-1.5-pro"
) -> Dict[str, Any]:
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        # Get video metadata
        metadata = get_video_metadata(video_path)

        # Upload and process video
        print("Uploading video...")
        video_file = genai.upload_file(path=video_path)
        
        while video_file.state.name == "PROCESSING":
            print('.', end='')
            time.sleep(10)
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            raise ValueError(f"Video processing failed: {video_file.state.name}")

        # Create prompt
        prompt = f"""You are an Expert Videographer that helps to storytell moments.
        1. Recognize the video and create a travel story about it.
        2. Script should be according to the length of the video: {metadata['duration']:.2f} seconds. Keep it short so it can be added to the video.
        3. Location: {location}
        4. Return response in JSON format with keys: story_text, duration_seconds, recommended_voice_tone
        """

        # Generate content
        print("\nGenerating Content...")
        response = model.generate_content(
            [video_file, prompt],
            request_options={"timeout": 600}
        )

        # Parse response and combine with metadata
        try:
            story_content = json.loads(response.text)
        except json.JSONDecodeError:
            story_content = {
                "story_text": response.text,
                "duration_seconds": metadata["duration"],
                "recommended_voice_tone": "neutral"
            }

        # Combine all information
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
    

# Test usage
if __name__ == "__main__":
    VIDEO_PATH = "IMG_5170.MOV"
    LOCATION = "Vangan Waterfall, Dang , Gujarat, India"
    API_KEY = dotenv.get_key(".env", "GEMINI_API_KEY")

    result = generate_video_story(
        video_path=VIDEO_PATH,
        location=LOCATION,
        api_key=API_KEY
    )
    
    print(json.dumps(result, indent=2))