# FramePlay
![FramePlay Banner](/assets/banner.png)

FramePlay is an innovative AI tool that transforms your videos and images into captivating stories. Our cutting-edge AI technology analyzes your media, creates a narrative, and produces a professionally edited video with narration. By combining advanced machine learning algorithms with creative storytelling techniques, FramePlay offers a unique way to bring your visual content to life.

## Key Features

- **AI-Powered Story Generation**: Our algorithms analyze your media to create compelling narratives that resonate with your audience.
- **Automatic Video Editing**: Seamlessly combine multiple videos and images into a cohesive story, complete with transitions and effects.
- **Natural Language Narration**: Add professional-sounding voiceovers to your videos automatically, choosing from a variety of voices and languages.
- **Smart Content Analysis**: Our AI detects key moments, emotions, and themes in your media to craft a meaningful narrative.

## How It Works

FramePlay uses a sophisticated AI pipeline to turn your media into a compelling story:

1. **Upload Your Content**: Simply upload your videos and images to our platform.
2. **AI Analysis**: Our algorithms analyze your media, detecting scenes, objects, emotions, and themes.
3. **Story Generation**: Based on the analysis, FramePlay crafts a narrative structure for your content.
4. **Automatic Editing**: The AI selects the best clips and images, arranging them into a coherent sequence.
5. **Voiceover Creation**: A natural-sounding narration is generated to guide viewers through your story.
6. **Download**: Download your video.

## Getting Started

### Prerequisites

- Python 3.9
- Required Python packages (listed in `requirements.txt`)

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/frameplay-ai/frameplay.git
    cd frameplay
    ```

2. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

3. Set up environment variables:
    Create a `.env` file in the root directory with the following content:
    ```properties
    AWS_ACCESS_KEY_ID=your_aws_access_key_id
    AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
    AWS_BUCKET=your_aws_bucket
    AWS_REGION=your_aws_region
    KESTRA_URL=your_kestra_url
    KESTRA_USERNAME=your_kestra_username
    KESTRA_PASSWORD=your_kestra_password
    S3_VID_BUCKET=your_s3_vid_bucket_url
    ```

### Running the Application

1. Start the Flask application:
    ```sh
    python app.py
    ```

2. Open your web browser and navigate to `http://localhost:5000`.

### Usage

1. **Home Page**: Provides an overview of FramePlay and its features.
2. **Create Page**: Allows users to upload their media files and create a story.
3. **Working Page**: Explains how FramePlay works.

## Kestra Workflow

FramePlay uses Kestra for orchestrating the video processing workflow. The Kestra workflow is defined in the `kestra_workflow.yml` file and includes the following steps:

1. **Download Video**: Downloads the uploaded video from the specified S3 bucket.
2. **Process Video and Generate Script**: Uses Google Generative AI to analyze the video and generate a travel story script.
3. **Generate Audio**: Converts the generated script into an audio file using AWS Polly.
4. **Merge Video and Audio**: Merges the video with the generated audio using FFmpeg.
5. **Upload Final Video**: Uploads the final video to the specified S3 bucket.

The workflow is triggered by a webhook and ensures that the entire process from video upload to final video generation is automated and efficient.

## Contributing

We welcome contributions to FramePlay! Please follow these steps to contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -am 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Create a new Pull Request.

## Screenshots
### Webpage
![1](/assets/screenshots/1.png)
![2](/assets/screenshots/2.png)
![3](/assets/screenshots/3.png)
![4](/assets/screenshots/4.png)

### Kestra
![1](/assets/screenshots/kestra1.png)
![2](/assets/screenshots/kestra2.png)
![3](/assets/screenshots/kestra3.png)
![4](/assets/screenshots/kestra4.png)

