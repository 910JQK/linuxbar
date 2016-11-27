import os
import imghdr
from flask import Blueprint, request, render_template, send_file, flash, abort
from flask_login import current_user, login_required


from utils import _
from utils import *
from models import Image
from forms import ImageUploadForm
from validation import REGEX_SHA256
from config import IMAGE_MIME, UPLOAD_FOLDER


image = Blueprint(
    'image', __name__, template_folder='templates', static_folder='static'
)


@image.route('/get/<sha256>')
def get(sha256):
    if REGEX_SHA256.fullmatch(sha256):
        img = find_record(Image, sha256=sha256)
        if img:
            mime = IMAGE_MIME[img.img_type]
            file_name = sha256 + '.' + img.img_type            
            path = os.path.join(UPLOAD_FOLDER, file_name)
            return send_file(path, mime)
        else:
            abort(404)
    else:
        abort(404)


@image.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    def sha256f(f):
        hash_sha256 = hashlib.sha256()
        for chunk in iter(lambda: f.read(4096), b''):
            hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    form = ImageUploadForm()
    if form.validate():
        img = form.image.data
        img_format = imghdr.what('', img.read(100))
        if IMAGE_MIME.get(img_format):
            img.seek(0)
            sha256 = sha256f(img)
            img.seek(0)
            if not find_record(Image, sha256=sha256):
                file_name = sha256 + '.' + img_format
                path = os.path.join(UPLOAD_FOLDER, file_name)
                img.save(path)
                Image.create(
                    sha256 = sha256,
                    uploader_id = current_user.id,
                    file_name = form.image.data.filename,
                    img_type = img_format,
                    date = now()
                )
                flash(_('Image uploaded successfully.'), 'ok')
            else:
                flash(_('An identical image already exists.'), 'err')
        else:
            flash(_('Invalid image format.'), 'err')
    return render_template('image/upload.html', form=form)
