from flask import Flask, request, jsonify
import requests
import os
import tempfile
import dotenv

dotenv.load_dotenv()

app = Flask(__name__)
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
TIKA_SERVER_URL = "http://localhost:9998/tika"

@app.route('/process-image', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files['image']

    # Save the uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        image_file.save(temp_file.name)
        temp_file_path = temp_file.name

    try:
        # Process the image with Tika
        with open(temp_file_path, 'rb') as file:
            tika_response = requests.put(TIKA_SERVER_URL, data=file)

        if tika_response.status_code != 200:
            return jsonify({"error": "Failed to process image with Tika"}), tika_response.status_code

        extracted_text = tika_response.text

        # Query Claude with the extracted text
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": ANTHROPIC_API_KEY
        }

        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": f"Answer the following question with just the right option and the answer in one line, no further explanation, ignore the watermarks in between \n: {extracted_text}"
                }
            ]
        }

        claude_response = requests.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers
        )

        if claude_response.status_code != 200:
            return jsonify({"error": "Failed to get response from Claude"}), claude_response.status_code

        claude_analysis = claude_response.json()['content'][0]['text']
        return jsonify({
            "extracted_text": extracted_text,
            "claude_analysis": claude_analysis
        })

    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

if __name__ == '__main__':
    app.run(debug=True)
    