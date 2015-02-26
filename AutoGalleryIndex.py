#!/usr/bin/python3

import flask
import os

app = flask.Flask(__name__)


@app.route('/<path:subfolder>')
def gallery(subfolder):
    DOCROOT = '/var/www'
    
    env_vars = {}
        
    request_root = '%s/%s' % (flask.request.script_root, subfolder)
    if request_root.endswith('/'):
        request_root = request_root[:-1]
    
    env_vars['gallery_root'] = flask.request.script_root

    env_vars['current_directory'] = DOCROOT + request_root
    env_vars['autogalleryindex_version'] = '0.1.0'
    
    env_vars['request_root'] = request_root
    env_vars['request_parent'] = '/'.join(request_root.split('/')[:-1])
    env_vars['subfolder'] = subfolder if subfolder.endswith('/') else subfolder + '/'

    symlink_src = DOCROOT + '/' + env_vars['gallery_root'] + '/'
    symlink_dest = DOCROOT + '/' + env_vars['gallery_root'] + '_static'
    if not os.path.exists(symlink_dest):
        os.symlink(symlink_src, symlink_dest)

    items = sorted(os.listdir(env_vars['current_directory']))
    env_vars['dir_contents'] = []
    for item in items:
        if os.path.isdir(env_vars['current_directory'] + '/' + item):
            env_vars['dir_contents'].append((item, 'd'))  # Directory
        else:
            env_vars['dir_contents'].append((item, 'f'))  # File

    return flask.render_template('Gallery.html', **env_vars)


@app.route('/')
def rootdir():
    return gallery('')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=True)
