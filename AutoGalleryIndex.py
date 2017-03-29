#!/usr/bin/env python3

import flask
import os
from PIL import Image, ImageFilter
import time
import subprocess

import FileMimetypes as mime

app = flask.Flask(__name__)
app.jinja_env.trim_blocks = True

RELEASE_VERSION = '1.0.0'

app.config['APPLICATION_NAME'] = 'AutoGalleryIndex'
app.config['ROW_ITEMS_SHORT'] = 3
app.config['ROW_ITEMS_LONG'] = 5
app.config['EXCLUDE_HIDDEN_FILES'] = True
app.config['MAX_LINE_CHARACTERS'] = 20
app.config['MAX_LINES_PER_ENTRY'] = 3

log_message = print


def get_cache_location():
    return os.path.join(app.config['CACHE_HOME'], app.config['APPLICATION_NAME'])


def is_mobile_request(request_headers):
    mobile_tags = ('Android', 'Windows Phone', 'iPod', 'iPhone')
    if any((tag in request_headers.get('User-Agent') for tag in mobile_tags)):
        return True
    return False


def get_directory_contents(directory):
    try:
        items = os.listdir(directory)
        if app.config['EXCLUDE_HIDDEN_FILES']:
            items = [i for i in items if not i.startswith('.')]
    except PermissionError as e:
        items = []

    return items


def grants_read_permission(path):
    """Only returns true if the specified file can be read"""
    if os.access(path, os.R_OK):
        return True
    return False

def grants_write_permission(path):
    """Returns True if the specified path has the write bit set for the current user or group"""
    if os.access(path, os.W_OK):
        return True
    return False


@app.before_first_request
def test_cache_directory():
    """Returns True if the cache is able to be used; Otherwise False"""
    cache_dir_path = get_cache_location()
    try:
        if not os.path.exists(cache_dir_path):
            os.makedirs(cache_dir_path)
        if not grants_write_permission(cache_dir_path):
            raise PermissionError
    except PermissionError as e:
        log_message('The current user (uid %d) does not have permission to write to %s' % (
                        os.getuid(), cache_dir_path))
        return False
    return True


def reformat_filename(filename):
    n_max = app.config['MAX_LINE_CHARACTERS']
    l_max = app.config['MAX_LINES_PER_ENTRY']

    if len(filename) < n_max:
        return filename

    # HTML will automatically split lines on '-' and ' '. Manually break up the filename at '_'
    result = ['']
    for s in filename.split('_'):
        if (len(result[-1]) + len(s) + 1) > n_max and len(s) < n_max:
            result.append('')
        result[-1] += ('_' if result[-1] else '') + s

    if len(result) > l_max:
        while len(result) > l_max:
            del result[l_max-2]
        result[-2] += '...'

    filename = ' '.join(result)

    return filename


@app.route('/<path:relpath>')
def gallery(relpath):
    template_vars = {}

    while relpath.endswith(os.path.sep):
        relpath = relpath[:-1]

    # from_root_relpath is the path from the apache webroot; relpath is only the path from the flask
    # script "root". from_root_relpath is only useful for transforming paths into absolute local paths
    from_root_relpath = os.path.join(flask.request.script_root, relpath).strip('/')
    template_vars['display_path'] = os.path.sep + os.path.join(from_root_relpath, '')

    abs_path = os.path.join(app.config['DOCROOT'], from_root_relpath)

    if not os.path.exists(abs_path):
        return flask.abort(404)

    if os.path.isfile(abs_path):
        return flask.send_from_directory(*os.path.split(abs_path))

    template_vars['dir_contents'] = []
    directory_items = get_directory_contents(abs_path)
    for item in directory_items:
        item_abs_path = os.path.join(abs_path, item)

        if not grants_read_permission(item_abs_path):
            continue

        file_type = mime.get_type(item_abs_path)

        item_relpath = os.path.join(relpath, item)

        item = reformat_filename(item)
        template_vars['dir_contents'].append((item, item_relpath, file_type))

    template_vars['dir_contents'].sort(key=lambda x: '..%s' % x[0].lower() if x[2] == mime.MIME_DIRECTORY else x[0].lower())
    # Insert a special entry for the "back" button if applicable
    if relpath:
        template_vars['dir_contents'].insert(0, ('Back',
                                                    os.path.dirname(relpath),
                                                    mime.MIME_DIRECTORY))

    if is_mobile_request(flask.request.headers):
        template_vars['items_per_row'] = app.config['ROW_ITEMS_SHORT']
    else:
        template_vars['items_per_row'] = app.config['ROW_ITEMS_LONG']

    for attr, value in ((attr, getattr(mime, attr)) for attr in dir(mime) if attr.startswith('MIME_')):
        template_vars[attr] = value

    template_vars['release_version'] = RELEASE_VERSION

    return flask.render_template('Gallery2.html', **template_vars)


@app.route('/')
def index():
    return gallery('')


if __name__ == '__main__':
    # For debugging only
    app.config['DOCROOT'] = '/var/www/html/GalleryDemo'
    app.config['CACHE_HOME'] = '/var/www/html/cache/'
    app.run(host='0.0.0.0', port=9001, debug=True)
