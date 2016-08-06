function AjaxForm(form, url, lock_form_after_ok, redirect_url) {
    this.form = form;
    this.message_box = form.querySelector('.message');
    this.submit_btn = form.querySelector('.submit_btn');
    this.url = url;
    this.lock_form_after_ok = Boolean(lock_form_after_ok);
    this.redirect_url = redirect_url;
    var captcha_input = form.querySelector('[name="captcha"]');
    if(captcha_input){
	this.has_captcha = true;
	this.captcha_image = form.querySelector('.captcha_image');
	this.captcha_input = captcha_input;
    } else {
	this.has_captcha = false;
    }
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
    if(result.code == 0){
	this.msg(result.msg, 'ok');
	if(this.lock_form_after_ok)
	    for(let input of this.form.querySelectorAll('input'))
		input.disabled = true;
	if(this.redirect_url)
	    setTimeout(() => location.replace(this.redirect_url), 800);
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
