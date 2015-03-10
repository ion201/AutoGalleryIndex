import sys
sys.path.insert(0, '/srv/AutoGalleryIndex')
import AutoGalleryIndex

AutoGalleryIndex.gallery.DOCROOT = '/var/www'

application = AutoGalleryIndex.app
