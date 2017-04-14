#!/usr/bin/env python3

import flask
import os
from PIL import Image, ImageFilter
import hashlib

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
app.config['THUMB_MAX_WIDTH'] = 178
app.config['THUMB_MAX_HEIGHT'] = 100
app.config['THUMB_IMAGE_TYPE'] = '.jpg'

log_message = print


class ThumbnailError(RuntimeError):
    pass


def get_cache_location_abs():
    return os.path.join(app.config['CACHE_ABS'], app.config['APPLICATION_NAME'])

def get_cache_location_url():
    abs_path = get_cache_location_abs()
    app.config['DOCROOT'] = app.config['DOCROOT']
    if app.config['DOCROOT'] not in abs_path:
        raise ValueError('The cache path (%s) must be inside the docroot (%s)' % (
                            app.config['DOCROOT'], abs_path))

    return abs_path.replace(app.config['DOCROOT'], '')

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


def get_cache_name_for_file(filepath):
    mtime = os.path.getmtime(filepath)
    basename = hashlib.sha1(('%s%f' % (filepath, mtime)).encode()).hexdigest()
    return basename + app.config['THUMB_IMAGE_TYPE']


def create_thumbnail(input_path, output_path):
    """Create a thumbnail and save output in filesystem
    output_path must be relative to cache home. Raises ThumbnailError on exceptions
    and returns the path relative to webroot on success"""
    if os.path.isabs(output_path):
        raise OSError('Could not create thumbnail: Path (%s) is not a relative path' % (
                                output_path,))

    if not os.path.isfile(input_path):
        raise ThumbnailError('The input path (%s) does not appear to be valid' % input_path)

    # Assume that this path has already been validated
    output_path_abs = os.path.join(get_cache_location_abs(), output_path)
    output_path_url = os.path.join(get_cache_location_url(), output_path)

    if not os.path.exists(output_path_abs):
        # Don't overwrite a pre-existing file

        try:
            thumb = Image.open(input_path)
            aspect_ratio = thumb.size[0] / thumb.size[1]
            if app.config['THUMB_MAX_WIDTH'] / aspect_ratio > app.config['THUMB_MAX_HEIGHT']:
                height = app.config['THUMB_MAX_HEIGHT']
                width = int(app.config['THUMB_MAX_HEIGHT'] * aspect_ratio)
            else:
                width = app.config['THUMB_MAX_WIDTH']
                height = int(app.config['THUMB_MAX_WIDTH'] / aspect_ratio)
            thumb = thumb.resize((width, height), Image.ANTIALIAS).filter(ImageFilter.DETAIL)
            thumb.save(output_path_abs)
        except Exception as e:
            # Lots of things could have gone wrong here. For now, just shove the information about
            # them into a single easily-caught exception
            raise ThumbnailError(repr(e))

    return output_path_url


@app.before_first_request
def test_cache_directory():
    """Returns True if the cache is able to be used; Otherwise False"""
    cache_dir_path = get_cache_location_abs()
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

        thumb_path = flask.url_for('static', filename=os.path.join('icons', file_type))
        if file_type == mime.MIME_IMAGE_GENERIC:
            thumb_cached_location = get_cache_name_for_file(item_abs_path)
            try:
                thumb_path = create_thumbnail(item_abs_path, thumb_cached_location)
                file_type = mime.MIME_IMAGE_THUMBED

            except ThumbnailError as e:
                log_message('Thumb error: %s' % str(e))


        item_relpath = os.path.join(relpath, item)

        item = reformat_filename(item)
        # Item = name shown on page
        # item_relpath = path to use for the link
        # File type = mime.MIME_XXX type
        # thumb_path = path to thumbnail for this item
        template_vars['dir_contents'].append((item, item_relpath, file_type, thumb_path))

    template_vars['dir_contents'].sort(key=lambda x: '..%s' % x[0].lower() if x[2] == mime.MIME_DIRECTORY else x[0].lower())
    # Insert a special entry for the "back" button if applicable
    if relpath:
        dir_icon_path = flask.url_for('static', filename=os.path.join('icons', mime.MIME_DIRECTORY))
        template_vars['dir_contents'].insert(0, ('Back',
                                                    os.path.dirname(relpath),
                                                    mime.MIME_DIRECTORY,
                                                    dir_icon_path))

    if is_mobile_request(flask.request.headers):
        template_vars['items_per_row'] = app.config['ROW_ITEMS_SHORT']
    else:
        template_vars['items_per_row'] = app.config['ROW_ITEMS_LONG']

    for attr, value in ((attr, getattr(mime, attr)) for attr in dir(mime) if attr.startswith('MIME_')):
        template_vars[attr] = value

    template_vars['release_version'] = RELEASE_VERSION

    return flask.render_template('Gallery.html', **template_vars)


@app.route('/')
def index():
    return gallery('')


if __name__ == '__main__':
    # For debugging only
    app.config['DOCROOT'] = '/var/www/html/GalleryDemo'
    app.config['CACHE_ABS'] = app.config['DOCROOT'] + '/cache'
    app.run(host='0.0.0.0', port=9001, debug=True)
