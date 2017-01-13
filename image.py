import os
import imghdr
from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    send_file,
    flash,
    abort,
    url_for,
    jsonify
)
from flask_login import current_user, login_required


from utils import _
from utils import *
from models import Config, User, Image
from forms import ImageUploadForm
from validation import REGEX_SHA256, REGEX_SHA256_PART
from config import IMAGE_MIME, UPLOAD_FOLDER


image = Blueprint(
    'image', __name__, template_folder='templates', static_folder='static'
)


def get_image_path(sha256, img_type):
    file_name = sha256 + '.' + img_type
    return os.path.join(UPLOAD_FOLDER, file_name)


@image.route('/get/<sha256part>')
def get(sha256part):
    if REGEX_SHA256_PART.fullmatch(sha256part):
        img_query = Image.select().where(Image.sha256.startswith(sha256part))
        if img_query:
            img = img_query.get()
            mime = IMAGE_MIME[img.img_type]
            return send_file(get_image_path(img.sha256, img.img_type), mime)
        else:
            abort(404)
    else:
        abort(404)


@image.route('/info/<sha256part>')
def info(sha256part):
    if REGEX_SHA256_PART.fullmatch(sha256part):
        img_query = Image.select().where(Image.sha256.startswith(sha256part))
        if img_query:
            img = img_query.get()
            return render_template(
                'image/info.html',
                img = img,
                sha256part = img.sha256[0:8]
            )
        else:
            abort(404)
    else:
        abort(404)


@image.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    output_json = bool(request.args.get('json'))
    def sha256f(f):
        hash_sha256 = hashlib.sha256()
        for chunk in iter(lambda: f.read(4096), b''):
            hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    pn = int(request.args.get('pn', '1'))
    count = int(Config.Get('count_item'))
    user = find_record(User, id=current_user.id)
    img_list = (
        Image
        .select()
        .where(Image.uploader == user)
        .order_by(Image.date.desc())
        .paginate(pn, count)
    )
    total = Image.select().where(Image.uploader == user).count()
    form = ImageUploadForm()
    if form.validate_on_submit():
        img = form.image.data
        img_type = imghdr.what('', img.read(100))
        if IMAGE_MIME.get(img_type):
            img.seek(0)
            sha256 = sha256f(img)
            img.seek(0)
            exist = find_record(Image, sha256=sha256)
            if not exist:
                img.save(get_image_path(sha256, img_type))
                Image.create(
                    sha256 = sha256,
                    uploader_id = current_user.id,
                    file_name = form.image.data.filename,
                    img_type = img_type,
                    date = now()
                )
                if output_json:
                    return jsonify({'code': 0, 'sha256': sha256})
                else:
                    flash(_('Image uploaded successfully.'), 'ok')
            else:
                if output_json:
                    return jsonify({'code': 0, 'sha256': exist.sha256})
                else:
                    flash(_('An identical image already exists.'), 'err')
        else:
            if output_json:
                return jsonify({'code': 1, 'msg': _('Invalid file format.')})
            else:
                flash(_('Invalid image format.'), 'err')
    if output_json:
        return jsonify({'code': 2, 'msg': _('No file selected.')})
    else:
        return render_template(
            'image/upload.html',
            form = form,
            img_list = img_list,
            pn = pn,
            count = count,
            total = total
        )


@image.route('/remove/<sha256>', methods=['GET', 'POST'])
@login_required
def remove(sha256):
    if REGEX_SHA256.fullmatch(sha256):
        img = find_record(Image, sha256=sha256)        
        if (
                img and (
                    img.uploader.id == current_user.id
                    or current_user.level > 0
                )
        ):
            if request.form.get('confirmed'):
                os.remove(get_image_path(img.sha256, img.img_type))
                img.delete_instance()
                flash(
                    _('Image %s deleted successfully.') % img.sha256[0:8], 'ok'
                )
                # if request is from link in info page, just show a message
                if request.args.get('info_page'):
                    return render_template('message.html')
                else:
                    return redirect(url_for('.upload'))
            else:
                return render_template(
                    'confirm.html',
                    text = (
                        _('Are you sure to delete image %s ?')
                        % img.sha256[0:8]
                    ),
                    url_no = request.args.get('info_page') or url_for('.upload')
                )
        else:
            abort(404)
    else:
        abort(404)
            
