#!/usr/bin/python3

import flask
import os
from PIL import Image, ImageFilter
import mimetypes
import time
import threading
import subprocess

app = flask.Flask(__name__)


def createdir(directory):
    #Create directory recursively
    if os.path.exists(directory):
        return
    if directory.endswith('/'):
        createdir(os.path.split(directory[:-1])[0])
    else:
        createdir(os.path.split(directory)[0])
    os.mkdir(directory)


def thumbnails(img_dir, thumb_dir, files_remaining, time_prev=0):
    """Generate thumbnails recursively from img_dir and save images to
    thumb_dir. Mirror source directory structure.
    Scans all subdirectories at once, so the first request
    may be very slow depending on the number of images found"""
    
    tmp_file = '/tmp/galleryindexcount'
    
    MAX_WIDTH = 178
    MAX_HEIGHT = 100
    
    image_types = ('.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.gif')
    
    try:
        dir_contents = os.listdir(img_dir)
    except Exception as e:
        return
    
    for file_name in dir_contents:
        files_remaining[0] -= 1
        if time.time() - time_prev > .05:
            with open(tmp_file, 'w') as f:
                f.write(str(files_remaining[0]))
                time_prev = time.time()

        abs_path = '%s/%s' % (img_dir, file_name)

        if file_name.startswith('.'):
            # Don't scan hidden files (This includes the thumbnail dir)
            continue
        
        if os.path.islink(abs_path):
            # Don't scan recursive symbolic links
            link_dest = os.path.realpath(abs_path)

            is_recursive = False

            next = os.path.split(abs_path)[0]
            while next != '/':
                if os.path.realpath(next) == link_dest:
                    is_recursive = True
                    break
                next = os.path.split(next)[0]
            
            if is_recursive:
                continue

        if os.path.isdir(abs_path):
            thumbnails(abs_path, '%s/%s' % (thumb_dir, file_name), files_remaining, time_prev)
            continue

        # Super inteligent file type detection
        if os.path.splitext(file_name)[-1].lower() not in image_types:
            continue  # Don't thumbnail non images (duh)

        thumb_dest = '%s/%s' % (thumb_dir, file_name)
        if not os.path.exists(thumb_dest):
            try:
                thumb = Image.open(abs_path)
                aspect_ratio = thumb.size[0] / thumb.size[1]
                if MAX_WIDTH / aspect_ratio > MAX_HEIGHT:
                    height = MAX_HEIGHT
                    width = int(MAX_HEIGHT * aspect_ratio)
                else:
                    width = MAX_WIDTH
                    height = int(MAX_WIDTH / aspect_ratio)
                thumb = thumb.resize((width, height), Image.ANTIALIAS).filter(ImageFilter.DETAIL)
                if not os.path.exists(thumb_dir):
                    # Create subdirectories only when needed
                    createdir(thumb_dir)
                thumb.save(thumb_dest)
            except Exception as e:
                # File could not be identified (probably). It's most likely not an image
                # This file will be given a generic icon when 
                pass


def get_type(item):
    if not mimetypes.inited:
        mimetypes.init()
    
    if item.endswith('.gz'):
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


def run_thumbnail_gen(script_root=None, total_files=None):
    # Symlink static files to make them accessible when apache is aliased over the actual directory
    # Creates directory ./<DOCROOT>._static next to ./<DOCROOT>
    # ./<DOCROOT>._static will be accessible via apache's normal autoindex unless explicity denied
    # in vhost configuration
    
    if not script_root:
        script_root = flask.request.script_root
    
    DOCROOT = gallery.DOCROOT
    symlink_src = DOCROOT + script_root + '/'
    symlink_dest = DOCROOT + script_root + '._static'
    if not os.path.exists(symlink_dest):
        os.symlink(symlink_src, symlink_dest)
    
    # Generate thumbnailails for ALL image files in directory
    if not os.path.exists(symlink_dest + '/._thumbnails'):
        os.mkdir(symlink_dest + '/._thumbnails')

    thumbnails(symlink_dest, symlink_dest + '/._thumbnails', total_files)
    with open('/tmp/galleryindexcount', 'w') as f:
        f.write('0')


def lib_maintainence(script_root):
    while True:
        # This beautiful command *quickly* recursively counts the number of objects in the directory
        # It's a list so that it can be passed by reference
        total_files = [int(subprocess.check_output('find %s/* | wc -l' % (gallery.DOCROOT + script_root),
                          shell=True).decode('utf-8'))]
        run_thumbnail_gen(script_root, total_files)
        # Scan for library changes every 5 minutes
        time.sleep(600)


@app.before_first_request
def maintainence_launcher():
    threading.Thread(target=lib_maintainence, args=(flask.request.script_root,)).start()


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
    env_vars['autogalleryindex_version'] = '0.5.1'
    
    env_vars['request_root'] = request_root
    env_vars['request_parent'] = '/' + '/'.join(list(filter(None, request_root.split('/')))[:-1])
    env_vars['subfolder'] = subfolder if (subfolder.endswith('/') or not subfolder) else subfolder + '/'

    items = os.listdir(env_vars['current_directory'])
    env_vars['dir_contents'] = []
    for item in items:
        if item.startswith('.'):
            # Don't mess with hidden files
            continue

        # Break up long names to allow line wrapping
        if any(len(part) >= 18 for part in item.split(' ')):
            parts = item.replace('_', '_ ').replace('.', '. ').split(' ')
            final_parts = ['']
            for subpart in parts:
                if len(final_parts[-1] + subpart) < 16:
                    final_parts[-1] += subpart
                else:
                    final_parts.append(subpart)
            item = ' '.join(final_parts)
        

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

    # Sort directories first, then sort by character
    env_vars['dir_contents'].sort(key=lambda x: '..%s' % x[0].lower() if x[1] == 'd' else x[0].lower())
    
    if env_vars['request_root'] != env_vars['request_parent']:  # == '/'
        env_vars['dir_contents'].insert(0, ('back', 'b'))
    
    mobile_tags = ('Android', 'Windows Phone', 'iPod', 'iPhone')
    # If it's a mobile browser, reduce the number of items displayed per row
    if any((tag in flask.request.headers.get('User-Agent') for tag in mobile_tags)):
        env_vars['items_per_row'] = 3
    else:
        env_vars['items_per_row'] = 5
   
    return flask.render_template('Gallery.html', **env_vars)


@app.route('/getthumbgenstatus/')
def getthumbgenstatus():
    with open('/tmp/galleryindexcount', 'r') as f:
        status = f.read()
    return status


@app.route('/')
def rootdir():
    return gallery('')


if __name__ == '__main__':
    # This is basically just for checking syntax errors. The program should
    # never be used without mod_wsgi and apache.
    gallery.DOCROOT = '/var/www/html/GalleryDemo'
    app.run(host='0.0.0.0', port=9001, debug=True)
