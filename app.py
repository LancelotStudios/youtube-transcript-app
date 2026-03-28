import os
import re
import logging
from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def extract_video_id(url):
    """Pull the video ID from common YouTube URL formats."""
    patterns = [
        r'(?:v=)([a-zA-Z0-9_-]{11})',       # youtube.com/watch?v=ID
        r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})', # youtu.be/ID
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
        # If a Webshare proxy token is configured, use it to avoid YouTube IP blocks
        proxy_token = os.environ.get('WEBSHARE_PROXY_TOKEN')
        if proxy_token:
            ytt = YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(proxy_token)
            )
        else:
            ytt = YouTubeTranscriptApi()

        transcript = ytt.fetch(video_id)
        text = ' '.join(entry.text for entry in transcript)
        return jsonify({'transcript': text})
    except Exception as e:
        app.logger.error(f'Transcript error for {video_id}: {type(e).__name__}: {e}')
        return jsonify({'error': f'Could not fetch transcript. Error: {type(e).__name__}. This video may not have captions, or YouTube may be blocking the request.'}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5001)

# Render uses gunicorn which imports 'app' directly from this module
