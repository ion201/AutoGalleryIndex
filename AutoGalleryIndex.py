#!/usr/bin/python3

import flask
import os

app = flask.Flask(__name__)

@app.route('/', methods=['GET'])
def rootdir():
    WEBROOT = '/var/www'

    env_vars = {}
    env_vars['current_directory'] = WEBROOT + flask.request.script_root
    env_vars['autogalleryindex_version'] = '0.1.0'

    return flask.render_template('Gallery.html', **env_vars)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=True)
