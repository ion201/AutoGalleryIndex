#!/usr/bin/python3

import flask
import os

app = flask.Flask(__name__)


@app.route('/', methods=['GET'])
def gallery():
    DOCROOT = '/var/www'
    
    env_vars = {}

    env_vars['current_directory'] = DOCROOT + flask.request.script_root
    env_vars['autogalleryindex_version'] = '0.1.0'

    if 'dest' in flask.request.args:
        if not os.path.exists(env_vars['current_directory'] + '_static'):
            os.symlink(env_vars['current_directory'], env_vars['current_directory'] + '_static')
        return flask.redirect(flask.request.script_root + '_static/' + flask.request.args['dest'])

    items = sorted(os.listdir(env_vars['current_directory']))
    env_vars['dir_contents'] = []
    for item in items:
        if os.path.isdir(env_vars['current_directory'] + '/' + item):
            env_vars['dir_contents'].append((item, 'd'))  # Directory
        else:
            env_vars['dir_contents'].append((item, 'f'))  # File

    return flask.render_template('Gallery.html', **env_vars)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=True)
