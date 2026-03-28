import os
import re
import logging
from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configure Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyDeI0DfIZYkb2GiUqWnE1sBMYX6rH8HbuI')
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def extract_video_id(url):
    """Pull the video ID from common YouTube URL formats."""
    patterns = [
        r'(?:v=)([a-zA-Z0-9_-]{11})',        # youtube.com/watch?v=ID
        r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',  # youtu.be/ID
        r'(?:embed/)([a-zA-Z0-9_-]{11})',      # youtube.com/embed/ID
        r'(?:shorts/)([a-zA-Z0-9_-]{11})',     # youtube.com/shorts/ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/transcript', methods=['POST'])
def get_transcript():
    url = request.json.get('url', '')
    video_id = extract_video_id(url)

    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL. Please paste a valid link.'}), 400

    try:
        ytt = YouTubeTranscriptApi()
        transcript = ytt.fetch(video_id)
        text = ' '.join(entry.text for entry in transcript)
        return jsonify({'transcript': text})
    except Exception as e:
        app.logger.error(f'Transcript error for {video_id}: {type(e).__name__}: {e}')
        return jsonify({'error': f'Could not fetch transcript. This video may not have captions available.'}), 400


@app.route('/summarize', methods=['POST'])
def summarize():
    transcript = request.json.get('transcript', '')

    if not transcript:
        return jsonify({'error': 'No transcript provided.'}), 400

    try:
        prompt = f"""Please analyze the following video transcript and provide:

1. **Summary**: A clear 2-3 sentence overview of what this video is about.
2. **Main Points**: The key takeaways as a bulleted list.
3. **Notable Quotes or Moments**: Any standout statements worth highlighting (if applicable).

Keep it concise and well-organized.

TRANSCRIPT:
{transcript}"""

        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return jsonify({'summary': response.text})
    except Exception as e:
        app.logger.error(f'Gemini error: {type(e).__name__}: {e}')
        return jsonify({'error': f'Could not generate summary. Please try again.'}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5001)
