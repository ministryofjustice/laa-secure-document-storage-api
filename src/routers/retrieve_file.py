from flask import Flask, request, jsonify
from src.services.s3_service import retrieveFileUrl

# Initialize Flask app
app = Flask(__name__)


# Route for retrieving files
@app.route('/retrieve_file', methods=['GET'])
def retrieve_file():
    # Get file key from request parameters
    file_key = request.args.get('file_name')

    if not file_key:
        return jsonify({'error': 'File key is missing'}), 400

    try:
        # Retrieve file from S3 bucket
        response = retrieveFileUrl(file_key)

        # Get file URL
        return jsonify({'fileURL': response}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Run Flask app
    app.run(debug=True)
