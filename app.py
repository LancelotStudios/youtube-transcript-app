import os
import re
import logging
import requests as req
from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi

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


def get_free_proxy():
    """Fetch a free proxy from Webshare's free proxy list using the API key."""
    api_key = os.environ.get('WEBSHARE_PROXY_TOKEN')
    if not api_key:
        return None
    try:
        resp = req.get(
            'https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page=1&page_size=10',
            headers={'Authorization': f'Token {api_key}'},
            timeout=10,
        )
        data = resp.json()
        results = data.get('results', [])
        if results:
            p = results[0]
            proxy_url = f"http://{p['username']}:{p['password']}@{p['proxy_address']}:{p['port']}"
            return proxy_url
    except Exception as e:
        app.logger.error(f'Proxy fetch error: {e}')
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
        # Try with a proxy first if available, fall back to direct
        proxy_url = get_free_proxy()
        if proxy_url:
            app.logger.info(f'Using proxy for {video_id}')
            session = req.Session()
            session.proxies = {'http': proxy_url, 'https': proxy_url}
            ytt = YouTubeTranscriptApi(http_client=session)
        else:
            app.logger.info(f'No proxy available, direct request for {video_id}')
            ytt = YouTubeTranscriptApi()

        transcript = ytt.fetch(video_id)
        text = ' '.join(entry.text for entry in transcript)
        return jsonify({'transcript': text})
    except Exception as e:
        app.logger.error(f'Transcript error for {video_id}: {type(e).__name__}: {e}')
        return jsonify({'error': f'Could not fetch transcript. Error: {type(e).__name__}. This video may not have captions, or YouTube may be blocking the request.'}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5001)
