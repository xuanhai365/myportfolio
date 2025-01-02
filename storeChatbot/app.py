import flask
from azure_setup import MyChatbot
import os

app = flask.Flask(__name__)

queries = []
chatbot = MyChatbot()

def process_query(queries):
    response = chatbot.get_response(queries[-1][1])
    response = response.replace('**', '*b*')
    response = response.replace('###', '*bb*')
    response = response.replace('\n', '*n*')
    split_response = response.split('*')
    processed_response = []
    bold = 0
    for word in split_response:
        flag = bold
        if word == 'b':
            word = ''
            if bold == 0:
                bold = 1
            else:
                bold = 0
        elif word == 'bb':
            word = ''
            bold = 2
        elif word == 'n':
            word = ''
            flag = -1
            if bold == 2:
                bold = 0
        processed_response.append([word, flag])
    return processed_response

@app.route('/')
def index():
    queries.clear()
    return flask.render_template('index.html', queries=queries)

@app.route('/search', methods=['POST', 'GET'])
def search():
    if flask.request.method == 'POST':
        query = ['user', flask.request.form['query']]
        queries.append(query)
        response = process_query(queries)
        queries.append(['bot', response])
    return flask.render_template('index.html', queries=queries)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)