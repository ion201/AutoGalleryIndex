# AutoGalleryIndex

mod_wsgi application designed to act similar to apache's autoindex but display thumbnail images. Primarily for viewing directories of images.

Steps to set up:

1. Follow sample in apache.txt for setting up vhost. For this example, AutoGalleryIndex is located in the /srv/ folder and the directory/subdirectories we want to replace with it is /filesnav/Sync/Photos.
2. In AutoGalleryIndex.wsgi, change the path in "sys.path.insert(0, '/srv/AutoGalleryIndex')" to reflect where you put this project's folder.
