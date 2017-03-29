import mimetypes
import os

# These type names match files in static/icons (except for 'i')
MIME_IMAGE_THUMBED = 'i'
MIME_DIRECTORY = 'folder.png'
MIME_IMAGE_GENERIC = 'image.png'
MIME_ARCHIVE = 'zip.png'
MIME_AUDIO = 'audio.png'
MIME_DISK = 'cd-image.png'
MIME_FONT = 'font.png'
MIME_DOC = 'office-doc.png'
MIME_PRESENT = 'office-present.png'
MIME_SPREADSHEET = 'office-spreadsheet.png'
MIME_PDF = 'pdf.png'
MIME_PYTHON = 'text-python.png'
MIME_SHELL = 'text-sh.png'
MIME_VIDEO = 'video.png'
MIME_PLAINTEXT = 'text-plain.png'
MIME_BINARY = 'binary.png'


def get_type(filepath):
    """Get simple text file type for a given file name"""
    if os.path.isdir(filepath):
        return MIME_DIRECTORY

    if not mimetypes.inited:
        mimetypes.init()

    # .gz does not return archive type as expected
    if filepath.endswith('.gz'):
        filepath += '.tgz'

    try:
        mime_type = mimetypes.types_map[os.path.splitext(filepath)[-1].lower()]
    except KeyError:
        mime_type = ''

    if mime_type.startswith('image'):
        return MIME_IMAGE_GENERIC

    elif any(tag in mime_type for tag in ('x-gtar', 'x-tar', 'zip', 'rar', 'x-7z')):
        return MIME_ARCHIVE

    elif 'audio' in mime_type:
        return MIME_AUDIO

    elif any(tag in mime_type for tag in ('iso9660-image', 'diskimage')):
        return MIME_DISK

    elif 'font' in mime_type:
        return MIME_FONT

    elif any(tag in mime_type for tag in ('msword', 'wordprocessingml.document', 'opendocument.text')):
        return MIME_DOC

    elif any(tag in mime_type for tag in ('powerpoint', 'presentation')):
        return MIME_PRESENT

    elif any(tag in mime_type for tag in ('spreadsheet', 'excel', 'text/csv')):
        return MIME_SPREADSHEET

    elif 'pdf' in mime_type:
        return MIME_PDF

    elif 'python' in mime_type:
        return MIME_PYTHON

    elif 'x-sh' in mime_type:
        return MIME_SHELL

    elif 'video' in mime_type:
        return MIME_VIDEO

    elif 'text' in mime_type:
        return MIME_PLAINTEXT

    return MIME_BINARY  # Generic file
