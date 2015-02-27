#!/usr/bin/python3

import flask
import os
from PIL import Image, ImageFilter

app = flask.Flask(__name__)


def thumbnails(img_dir, thumb_dir):
    os.chdir('/srv/AutoGalleryIndex')
    if not os.path.exists(thumb_dir):
        os.mkdir(thumb_dir)
    image_types = ('.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.tff')
    for file_name in os.listdir(img_dir):
        abs_path = '%s/%s' % (img_dir, file_name)
        
        if '._thumbnails' == file_name:
            continue
        
        if os.path.isdir(abs_path):
            thumbnails(abs_path, '%s/%s' % (thumb_dir, file_name))
            continue
            
        # Super inteligent file type detection
        if os.path.splitext(file_name)[-1].lower() not in image_types:
            continue  # Don't thumbnail non images (duh)
        
        thumb_dest = '%s/%s' % (thumb_dir, file_name)
        #if not os.path.exists(thumb_dest):
        thumb = Image.open(abs_path).resize((100, 178), Image.ANTIALIAS).filter(ImageFilter.DETAIL)
        thumb.save(thumb_dest)


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
    env_vars['subfolder'] = subfolder if (subfolder.endswith('/') or not subfolder) else subfolder + '/'

    # Symlink static files to make them accessible when apache is aliased over the actual directory
    symlink_src = DOCROOT + env_vars['gallery_root'] + '/'
    symlink_dest = DOCROOT + env_vars['gallery_root'] + '._static'
    if not os.path.exists(symlink_dest):
        os.symlink(symlink_src, symlink_dest)
    
    # Generate thumbnailails for image files
    if not os.path.exists(symlink_dest + '/._thumbnails'):
        os.mkdir(symlink_dest + '/._thumbnails')
    thumbnails(symlink_dest, symlink_dest + '/._thumbnails')

    items = sorted(os.listdir(env_vars['current_directory']))
    env_vars['dir_contents'] = []
    for item in items:
        if item == '._thumbnails':
            pass
        elif os.path.isdir(env_vars['current_directory'] + '/' + item):
            env_vars['dir_contents'].append((item, 'd'))  # Directory
        else:
            env_vars['dir_contents'].append((item, 'f'))  # File

    return flask.render_template('Gallery.html', **env_vars)


@app.route('/')
def rootdir():
    return gallery('')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=True)
