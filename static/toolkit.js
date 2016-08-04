var query = selector => document.querySelector(selector);
var query_all = selector => document.querySelectorAll(selector);


/* Reserved for l10n */
function _(string) {
    return string;
}


/**
 * Return a copy of "str" with placeholders replaced by the rest arguments.
 * @param String str
 * @param String ...args
 * @return String
 */
function printf(){
    var str = arguments[0];
    var args = arguments;
    str = str.replace(/%(\d+)|%{(\d+)}/g, function(match, number1, number2){
	var number = number1? number1: number2;
	return (typeof args[number] != 'undefined')? args[number]: match;
    });
    return str;
}


/**
 * Send a GET request.
 *
 * @param String url
 * @param Object data
 * @param Function ok(XMLHttpRequest xhr)
 * @param Function err(Number status, String statusText)
 * @param Number timeout = 2000
 * @return XMLHttpRequest
 */
function GET(url, data, ok, err, timeout) {
    var params = Object.keys(data).map(
	k => encodeURIComponent(k) + '=' + encodeURIComponent(data[k])
    ).join('&');
    var xhr = new XMLHttpRequest();
    if(params)
	url = url + '?' + params;
    xhr.open('GET', url);
    xhr.timeout = timeout? timeout: 2000;
    xhr.onreadystatechange = function() {
	if(xhr.readyState == 4) {
	    if(xhr.status == 200)
		ok(xhr);
	    else
		err(xhr.status, xhr.statusText);
	}
    };
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.send();
    return xhr;
}


/**
 * Send a POST request.
 *
 * @param String url
 * @param Object data
 * @param Function ok(XMLHttpRequest xhr)
 * @param Function err(Number status, String statusText)
 * @param Number timeout = 2000
 * @return XMLHttpRequest
 */
function POST(url, data, ok, err, timeout) {
    var params;
    if(data instanceof FormData) {
	params = data;
    } else {
	params = Object.keys(data).map(
	    k => encodeURIComponent(k) + '=' + encodeURIComponent(data[k])
	).join('&');
    }
    var xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    xhr.timeout = timeout? timeout: 2000;
    xhr.onreadystatechange = function() {
	if(xhr.readyState == 4) {
	    if(xhr.status == 200)
		ok(xhr);
	    else
		err(xhr.status, xhr.statusText);
	}
    };
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    if(typeof params == 'string') {
	xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
	xhr.setRequestHeader('Content-length', params.length);
    }
    xhr.send(params);
    return xhr;
}


/**
 * Return the real length of a string
 *
 * @param String string
 * @return Number
 */
function strlen(string) {
    return Array.from(string).length;
}


/**
 * Return the count of bytes (in UTF-8) of a string
 *
 * @param String string
 * @return Number
 */
function utf8sizeof(string) {
    /* JavaScript uses UCS-2, not supporting 4-byte UTF-16 characters. */
    return unescape(encodeURIComponent(string)).length;
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
}


/**
 * Show validation message in the description field below an `<input>`.
 * Change event handler for form validation.
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
	input.addEventListener('change', show_validation_message);
	if(realtime){
	    input.addEventListener('keyup', validate_size);
	    input.addEventListener('keyup', show_validation_message);
	}
	/* The browser may save the previous data. */
	if(input.value)
	    validate_size.call(input);
    }
    var input_confirm = query('input[name="password_confirm"]');
    if(input_confirm) {
	let input_password = query('input[name="password"]');
	input_confirm.addEventListener('change', validate_password_confirmation);
	/* Validation of password confirmation should not be realtime. */
	input_confirm.addEventListener('change', show_validation_message);

	input_password.addEventListener('change', function(){
	    input_confirm.value = '';
	});
    }
}
