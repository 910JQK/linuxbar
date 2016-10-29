var format_checking = false;
var reader = new FileReader();


/**
 * Check if header bytes of a file or a blob matches one of specified formats.
 *
 * @param Blob blob
 * @param Array headers (2d array)
 * @param Function callback
 * @return void
 */
function check_file_format(blob, headers, callback) {
    if(format_checking){
	reader.abort();
	reader = new FileReader();
    }
    format_checking = true;
    reader.addEventListener('loadend', function() {
	var arr = new Uint8Array(reader.result);
	/* valid if one of these formats is matched */
	var ok_outer = false;
	for(let header of headers) {
	    let ok = true;
	    for(let i=0; i<header.length; i++) {
		if(!arr[i] || arr[i] != header[i]) {
		    ok = false;
		    break;
		}
	    }
	    if(ok) {
		ok_outer = true;
		break;
	    }
	}
	callback(ok_outer);
	format_checking = false;
    });
    reader.addEventListener('error', function() {
	callback(false);
	format_checking = false;
    });
    var segment = blob.slice(0, 100);
    reader.readAsArrayBuffer(segment);
}


/**
 * Check if the UTF-8 size of the value of an `<input>` is in proper range.
 * Change event handler for form validation.
 *
 * @this HTMLInputElement
 * @return void
 */
function validate_size() {
    var size = utf8sizeof(this.value);
    var min = Number.parseInt(this.dataset.min);
    var max = Number.parseInt(this.dataset.max);
    if(size < min)
	this.setCustomValidity(
	    printf(_('%1 should be at least %2 bytes.'), this.placeholder, min)
	);
    else if(size > max)
	this.setCustomValidity(
	    printf(_('%1 should be at most %2 bytes.'), this.placeholder, max)
	);
    else
	this.setCustomValidity('');
    show_validation_message.call(this);
}


/**
 * Check if two password fields are consistent.
 * Change event handler for form validation.
 *
 * @this HTMLInputElement
 * @return void
 */
function validate_password_confirmation() {
    var password_input = query('input[name="password"]');
    if(this.value != password_input.value)
	this.setCustomValidity(_('Two fields are inconsistent.'));
    else
	this.setCustomValidity('');
    show_validation_message.call(this);
}


/**
 * Check if a file matches specified format.
 * Change event handler for form validation.
 *
 * @this HTMLInputElement
 * @return void
 */
function validate_file() {
    /* formats: 2d array */
    var formats = JSON.parse(this.dataset.formats);
    var file = this.files[0];
    if(!file)
	return;
    var input = this;
    check_file_format(file, formats, function(ok) {
	if(!ok)
	    input.setCustomValidity(_('Invalid file format.'));
	else
	    input.setCustomValidity('');
	show_validation_message.call(input);
    });
}


/**
 * Show validation message in the description field below an `<input>`.
 * Indirect change event handler for form validation.
 *
 * @this HTMLInputElement
 * @return void
 */
function show_validation_message() {
    var desc = this.nextElementSibling;
    if(this.validity.valid) {
	desc.textContent = desc.dataset.desc;
	desc.dataset.color = '';
    } else {
	desc.textContent = this.validationMessage;
	if(this.value === '')
	    desc.textContent = printf(
		_('%1 cannot be empty.'),
		this.placeholder
	    );
	desc.dataset.color = 'err';
    }
}


/**
 * Add event handlers for size-type and password-confirmation form validation.
 *
 * @param Boolean realtime
 * @return void
 */
function init_validation(realtime) {
    /* Don't use the following methods together. */
    /* A custom validation will conflict with another. */
    for(let input of query_all('input[data-min], input[data-max]')) {
	input.addEventListener('change', validate_size);
	if(realtime){
	    input.addEventListener('keyup', validate_size);
	}
	/* The browser may save the previous data. */
	if(input.value)
	    validate_size.call(input);
    }
    for(let input of query_all('input[data-formats]')) {
	input.addEventListener('change', validate_file);
    }
    var input_confirm = query('input[name="password_confirm"]');
    if(input_confirm) {
	let input_password = query('input[name="password"]');
	input_confirm.addEventListener('change', validate_password_confirmation);
	/* Validation of password confirmation should not be realtime. */
	input_password.addEventListener('change', function(){
	    input_confirm.value = '';
	});
    }
}


function AjaxForm(form, url, lock_form_after_ok, redirect_url, success_callback, options) {
    var controller = this;
    this.form = form;
    this.message_box = form.querySelector('.message');
    this.submit_btn = form.querySelector('.submit_btn');
    this.url = url;
    this.lock_form_after_ok = Boolean(lock_form_after_ok);
    this.redirect_url = redirect_url;
    var match = location.search.match(/ret=([^&]*)/);
    if(match && match[1])
	this.redirect_url = decodeURIComponent(match[1]);
    var captcha_input = form.querySelector('[name="captcha"]');
    var captcha_image;
    if(captcha_input) {
	this.has_captcha = true;
	this.captcha_image = form.querySelector('.captcha_image');
	this.captcha_input = captcha_input;
	captcha_image = form.querySelector('img.captcha_image');
	captcha_image.addEventListener('click', function() {
	    controller.refresh_captcha();
	    controller.focus_captcha_input();
	});
    } else {
	this.has_captcha = false;
    }
    this.success_callback = success_callback;
    if(options)
	this.options = options;
    else
	this.options = {};
    var content = form.querySelector('[name="content"]');
    if(content)
	content.addEventListener('keydown', function(ev) {
	    if(ev.key == 'Enter' && ev.ctrlKey) {
		ev.preventDefault();
		if(form.reportValidity){
		    /* not implemented in Firefox now */
		    if(form.reportValidity())
			controller.submit();
		} else {
		    controller.submit();
		}
	    }
	});
    this.submit_btn.addEventListener('click', this.submit.bind(this));
}


AjaxForm.prototype.msg = function(text, type){
    var message = this.message_box;
    message.textContent = text;
    if(type == 'ok')
	message.dataset.color = 'ok';
    else if(type == 'err')
	     message.dataset.color = 'err';
    else
	message.dataset.color = 'loading';
};


AjaxForm.prototype.empty = function() {
    this.message_box.textContent = '';
    for(let input of this.form.querySelectorAll(
	'input[type="text"], input[type="password"], textarea'
    )) {
	input.value = '';
    }
};


AjaxForm.prototype.submit = function() {
    POST(
	this.url,
	new FormData(this.form),
	this.ok.bind(this),
	this.err.bind(this)
    );
    this.submit_btn.disabled = true;
    this.msg(_('Loading ...'));
};


AjaxForm.prototype.ok = function(xhr) {
    this.submit_btn.disabled = false;
    var result = JSON.parse(xhr.responseText);
    if(result.code == 0) {
	this.msg(result.msg, 'ok');
	if(this.lock_form_after_ok)
	    for(let input of this.form.querySelectorAll('input'))
		input.disabled = true;
	if(this.success_callback)
	    this.success_callback(result);
	if(this.redirect_url)
	    setTimeout(
		() => location.replace(this.redirect_url),
		(this.options.redirect_delay || 800)
	    );
    } else {
	this.msg(result.msg, 'err');
	if(this.has_captcha) {
	    this.refresh_captcha();
	    /* 250: wrong captcha */
	    if(result.code == 250)
		this.focus_captcha_input();
	}
    }
};


AjaxForm.prototype.err = function(status, text) {
    this.submit_btn.disabled = false;
    if(status != 0)
	this.msg(printf(_('Error: %1 %2'), status, text), 'err');
    else
	this.msg(_('Connection Error or Timeout'), 'err');
};


AjaxForm.prototype.refresh_captcha = function() {
    this.captcha_input.value = '';
    this.captcha_image.src = (
	'/captcha/get?' + new Date().getTime()
    );
};


AjaxForm.prototype.focus_captcha_input = function() {
    this.captcha_input.focus();
};
