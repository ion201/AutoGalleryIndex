# AutoGalleryIndex

mod_wsgi application designed to act similar to apache's autoindex but display thumbnail images. Primarily for viewing directories of images. Demo page: http://cloud.natesimon.me/GalleryDemo/

Dependencies:

* apache
* python3.x
* mod_wsgi (python3)

Debian and derivatives:

`sudo apt-get install python3-dev libjpeg-dev libtiff5-dev libpng12-dev`

Basic setup:

1. Follow sample in apache.txt for setting up vhost. For this example, AutoGalleryIndex is located in the /srv/ folder and the directory/subdirectories we want to replace with it is /filesnav/Sync/Photos.
2. In the wsgi file for each directory you are replacing, set the docroot and path to the appropriate locations.
