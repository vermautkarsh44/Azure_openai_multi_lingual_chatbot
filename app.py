from flask import Flask, request, jsonify
from flask_cors import CORS
from src import azure_translator
from src.utils import qna, upload_pdf

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})
error = None

@app.route('/')
def hello():
    return 'Welcome to Multi-Lingual CT Miner!'

@app.route('/qna', methods=['POST'])
def qna_api():
    data = request.get_json()

    query = data['query']
    conversation_id = data['conversation_id']
    model = data['model']
    query_language = data['query_language']

    if(model == 'gpt-3.5'):
        model = 'gpt-35-turbo'
    else:
        model = 'gpt-4-1106-preview'

    try:
        qna_response = qna(query, conversation_id, model, query_language)
        response = jsonify(qna_response)
        response.status_code = 200
        return response
    except Exception as e:
        return {'pdf_name':'',
                'answer': e.__str__()
        }

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    data = request.get_json()

    pdf_path = data['pdf_path']
    pdf_name = data['pdf_name']
    conversation_id = data['conversation_id']

    try:
        result = upload_pdf(pdf_path, pdf_name, conversation_id)
        if result:
            response = jsonify({'result': 'PDF successfully uploaded and ready for QnA!'})
            return response
    except Exception as e:
        return {'result': e.__str__()}

if __name__ == '__main__':
    app.run(debug=True, port=8000, use_reloader=False)