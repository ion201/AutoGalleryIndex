#!/usr/bin/python3

import flask
import os
from PIL import Image, ImageFilter
import mimetypes
import time
import threading

app = flask.Flask(__name__)


def thumbnails(img_dir, thumb_dir):
    """Generate thumbnails recursively from img_dir and save images to
    thumb_dir. Mirror source directory structure.
    Scans all subdirectories at once, so the first request
    may be very slow depending on the number of images found"""
    
    if not os.path.exists(thumb_dir):
        os.mkdir(thumb_dir)
    image_types = ('.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.gif')
    
    try:
        dir_contents = os.listdir(img_dir)
    except Exception as e:
        return
    
    for file_name in dir_contents:
        abs_path = '%s/%s' % (img_dir, file_name)
        
        if file_name.startswith('.'):
            # Don't scan hidden files (This includes the thumbnail dir)
            continue
        
        if os.path.isdir(abs_path):
            thumbnails(abs_path, '%s/%s' % (thumb_dir, file_name))
            continue
            
        # Super inteligent file type detection
        if os.path.splitext(file_name)[-1].lower() not in image_types:
            continue  # Don't thumbnail non images (duh)
        
        thumb_dest = '%s/%s' % (thumb_dir, file_name)
        if not os.path.exists(thumb_dest):
            try:
                thumb = Image.open(abs_path).resize((178, 100), Image.ANTIALIAS).filter(ImageFilter.DETAIL)
                thumb.save(thumb_dest)
            except Exception as e:
                # File could not be identified (probably). It's most likely not an image
                # This file will be given a generic icon when 
                pass


def get_type(item):
    if not mimetypes.inited:
        mimetypes.init()
    
    if item.endswith('.tar.gz'):
        item += '.tgz'  # Annoying anomaly

    try:
        mime_type = mimetypes.types_map[os.path.splitext(item)[-1].lower()]
    except KeyError:
        mime_type = ''

    if mime_type.startswith('image'):
        return 'i'  # image

    elif any(tag in mime_type for tag in ('x-gtar', 'x-tar', 'zip', 'rar', 'x-7z')):
        return 'zip'  # Archive
        
    elif 'audio' in mime_type:
        return 'audio'
    
    elif any(tag in mime_type for tag in ('iso9660-image', 'diskimage')):
        return 'cd-image'
    
    elif 'font' in mime_type:
        return 'font'

    elif any(tag in mime_type for tag in ('msword', 'wordprocessingml.document', 'opendocument.text')):
        return 'office-doc'
    
    elif any(tag in mime_type for tag in ('powerpoint', 'presentation')):
        return 'office-present'
    
    elif any(tag in mime_type for tag in ('spreadsheet', 'excel', 'text/csv')):
        return 'office-spreadsheet'
    
    elif 'pdf' in mime_type:
        return 'pdf'
    
    elif 'python' in mime_type:
        return 'text-python'
    
    elif 'x-sh' in mime_type:
        return 'text-sh'
    
    elif 'video' in mime_type:
        return 'video'
        
    elif 'text' in mime_type:
        return 'text-plain'

    return 'binary'  # Generic file


def run_thumbnail_gen():
    # Symlink static files to make them accessible when apache is aliased over the actual directory
    # Creates directory ./<DOCROOT>._static next to ./<DOCROOT>
    # ./<DOCROOT>._static will be accessible via apache's normal autoindex unless explicity denied
    # in vhost configuration
    DOCROOT = gallery.DOCROOT
    symlink_src = DOCROOT + flask.request.script_root + '/'
    symlink_dest = DOCROOT + flask.request.script_root + '._static'
    if not os.path.exists(symlink_dest):
        os.symlink(symlink_src, symlink_dest)
    
    # Generate thumbnailails for ALL image files in directory
    if not os.path.exists(symlink_dest + '/._thumbnails'):
        os.mkdir(symlink_dest + '/._thumbnails')
        
    thumbnails(symlink_dest, symlink_dest + '/._thumbnails')


def lib_maintainence():
    while True:
        # Scan for library changes every 5 minutes
        run_thumbnail_gen()
        time.sleep(600)


@app.before_first_request
def maintainence_launcher():
    threading.Thread(target=lib_maintainence).start()


@app.route('/<path:subfolder>')
def gallery(subfolder):
    DOCROOT = gallery.DOCROOT
    
    env_vars = {}
        
    request_root = '%s/%s' % (flask.request.script_root, subfolder)
    if request_root.endswith('/'):
        request_root = request_root[:-1]
    
    env_vars['gallery_root'] = flask.request.script_root

    env_vars['current_directory'] = DOCROOT + request_root
    # Version is arbitrarily incremented to create the illusion of progress
    env_vars['autogalleryindex_version'] = '0.4.0'
    
    env_vars['request_root'] = request_root
    env_vars['request_parent'] = '/'.join(request_root.split('/')[:-1])
    env_vars['subfolder'] = subfolder if (subfolder.endswith('/') or not subfolder) else subfolder + '/'

    items = os.listdir(env_vars['current_directory'])
    env_vars['dir_contents'] = []
    for item in items:
        if item.startswith('.'):
            # Don't mess with hidden files
            continue
        if os.path.isdir(env_vars['current_directory'] + '/' + item):
            env_vars['dir_contents'].append((item, 'd'))  # Directory
            continue
    
        file_type = get_type(item)
        if file_type == 'i':
            if not os.path.exists('%s/._thumbnails/%s%s' % (
                                   DOCROOT + env_vars['gallery_root'] + '._static',
                                   env_vars['subfolder'], item)):
                file_type = 'image'
        env_vars['dir_contents'].append((item, file_type))

    # Sort directories first
    env_vars['dir_contents'].sort(key=lambda x: '..' if x[1] == 'd' else x[0].lower())
    env_vars['dir_contents'].insert(0, ('back', 'b'))
    
    mobile_tags = ('Android', 'Windows Phone', 'iPod', 'iPhone')
    # If it's a mobile browser, reduce the number of items displayed per row
    if any((tag in flask.request.headers.get('User-Agent') for tag in mobile_tags)):
        env_vars['items_per_row'] = 3
    else:
        env_vars['items_per_row'] = 5
   
    return flask.render_template('Gallery.html', **env_vars)


@app.route('/makethumbs/')
def makethumbs():
    run_thumbnail_gen()
    return flask.redirect('/')


@app.route('/')
def rootdir():
    return gallery('')


if __name__ == '__main__':
    # This is basically just for checking syntax errors. The program should
    # never be used without mod_wsgi and apache.
    app.run(host='0.0.0.0', port=9001, debug=True)
