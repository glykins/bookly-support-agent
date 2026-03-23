from flask import Flask, request, jsonify, send_from_directory
from agent import run_agent

app = Flask(__name__, static_folder='static')

conversations = {}

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    session_id = data.get('session_id', 'default')
    user_message = data.get('message', '')

    if not user_message.strip():
        return jsonify({'error': 'No message provided'}), 400

    history = conversations.get(session_id, [])

    try:
        response, updated_history = run_agent(history, user_message)
        conversations[session_id] = updated_history
        return jsonify({'response': response, 'session_id': session_id})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset():
    data = request.get_json()
    session_id = data.get('session_id', 'default')
    conversations[session_id] = []
    return jsonify({'status': 'reset'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
