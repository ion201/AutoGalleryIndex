#!/usr/bin/python3

import flask

app = flask.Flask(__name__)

@app.route('/', methods=['GET'])
def rootdir():
    return 'hello world'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=True)
