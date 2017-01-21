var query = selector => document.querySelector(selector);
var query_all = selector => document.querySelectorAll(selector);
var _ = str => str; // reserved for l10n
var timer = new Worker('/static/timer.js');
var TITLE_MAX_SIZE= 64;


/**
 * Return the UTF-8 byte count of `str`
 *
 * @param String str
 * @return Number
 */
function utf8size(str) {
    return unescape(encodeURIComponent(str)).length;
}


/**
 * Return a copy of `str` with placeholders replaced by the rest arguments.
 *
 * @param String str
 * @param String ...args
 * @return String
 */
function printf() {
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
 * @param Number timeout = 6000
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
    xhr.timeout = timeout? timeout: 6000;
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
 * @param Number timeout = 6000
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
    xhr.timeout = timeout? timeout: 6000;
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
 * Cancel a link so that javascript event can make sense
 *
 * @param Object link
 * @return void
 */
function cancel_link(link) {
    link.href = 'javascript: void(0)';
    link.target = '';
}


/**
 * Format date
 *
 * @param Number timestamp
 * @return String
 */
function format_date(timestamp) {
    /* behaviour of this function must be consistent with the back-end */
    var now = (Date.now() / 1000);
    var delta = Math.round(now - timestamp);
    if(delta < 60){
        return _('just now');
    } else if(delta < 3600) {
        let minutes = Math.floor(delta / 60);
	if(minutes == 1)
            return _('a minute ago');
        else
            return printf(_('%1 minutes ago'), minutes);
    } else if(delta < 86400) {
        let hours = Math.floor(delta / 3600);
        if(hours == 1)
            return _('an hour ago');
        else
            return printf(_('%1 hours ago'), hours);
    /*  604800 = 86400*7  */
    } else if(delta < 604800) {
        let days = Math.floor(delta / 86400);
        if(days == 1)
            return _('a day ago');
        else
            return printf(_('%1 days ago'), days);
    /* 2629746 = 86400*(31+28+97/400+31+30+31+30+31+31+30+31+30+31)/12 */
    } else if(delta < 2629746) {
        let weeks = Math.floor(delta / 604800);
        if(weeks == 1)
            return _('a week ago');
        else
            return printf(_('%1 weeks ago'), weeks);
    /* 31556952 = 86400*(365+97/400) */
    } else if(delta < 31556952) {
        let months = Math.floor(delta / 2629746);
        if(months == 1)
            return _('a month ago');
        else
            return printf(_('%1 months ago'), months);
    } else {
        let years = Math.floor(delta / 31556952);
        if(years == 1)
            return _('a year ago');
        else
            return printf(_('%1 years ago'), years);
    }
}


/**
 * Update unread count info in user toolbar
 *
 * @return void
 */
function update_unread_info() {
    if(!query('#link_notify_reply'))
	return;
    GET(
	'/user/unread-info',
	{},
	function(xhr) {
	    function try_to_highlight(link, n) {
		if(n > 0 && !link.classList.contains('link_highlight'))
		    link.classList.add('link_highlight');
		else if(n == 0 && link.classList.contains('link_highlight'))
		    link.classList.remove('link_highlight');
	    }
	    var result = JSON.parse(xhr.responseText);
	    var total = 0;
	    for(let item of Object.keys(result)) {
		let link = query(printf('#link_notify_%1', item));
		let n = result[item];
		link.textContent = (
		    printf('%1(%2)', link.dataset.content, n)
		);
		try_to_highlight(link, n);
		total += n;
	    }
	    link_notify_all.firstElementChild.innerText = total.toString();
	    try_to_highlight(link_notify_all, total);
	},
	function(status, text) {
	    console.error(
		printf('Failed to get unread count: %1 %2', status, text)
	    );
	}
    );
}


/**
 * Update relative datetime of all date spans on the page
 *
 * @return void
 */
function update_date() {
    for(let span of query_all('.date')) {
	span.textContent = format_date(span.dataset.ts);
    }
}


/**
 * Enable the timer to update unread info
 *
 * @return void
 */
function init_unread_info_timer() {
    timer.addEventListener('message', function(ev) {
	if(ev.data == 'update_unread_info') {
	    if(!document.hidden) {
		// only check when the page is foreground
		update_unread_info();
	    }
	}
    });
}


/**
 * Enable the timer to update relative datetime
 *
 * @return void
 */
function init_datetime_timer() {
    timer.addEventListener('message', function(ev) {
	if(ev.data == 'update_date')
	    update_date();
    });
}


/**
 * Initialize the tag selector
 *
 * @return void
 */
function init_tag_selector() {
    if(query('#tag_selector')) {
	let fieldset = query('#add_topic_form > fieldset');
	let banned = fieldset && fieldset.disabled;
	let tags_input = query('select[name="tags"]');
	for(let I of tags_input.options) {
	    let option = I;
	    let checkbox = (
		tag_selector.querySelector(
		    printf('input[data-slug="%1"]', option.value)
		)
	    );
	    let event_handler = function() {
		option.selected = this.checked;
	    };
	    checkbox.addEventListener('change', event_handler);
	    event_handler.call(checkbox);
	    if(!banned) {
		checkbox.parentElement.addEventListener('click', function(ev) {
		    if(ev.target != checkbox)
			checkbox.checked = !checkbox.checked;
		});
	    } else {
		checkbox.parentElement.style.color = 'gray';
	    }
	    checkbox.nextElementSibling.unselectable = 'on';
	    checkbox.nextElementSibling.onselectstart = (function() {
		return false;
	    });
	}
	tags_input.style.display = 'none';
	tag_selector.style.display = '';
    }
}


/**
 * Add addtional features to forms
 *
 * @return void
 */
function init_forms() {
    if(query('#add_topic_form')) {
	let title = add_topic_form.querySelector('[name="title"]');
	let content = add_topic_form.querySelector('[name="content"]');
	let validate = function() {
	    if(!title.value) {
		alert(_('Title cannot be empty.'));
	    } else if (!content.value) {
		alert(_('Content cannot be empty.'));
	    } else if(utf8size(title.value) > TITLE_MAX_SIZE) {
		alert(
		    printf(_('Title cannot exceed %1 bytes.'), TITLE_MAX_SIZE)
		);
	    } else {
		return true;
	    }
	    return false;
	};
	content.addEventListener('keyup', function(ev) {
	    if(ev.key == 'Enter' && ev.ctrlKey) {
		ev.preventDefault();
		if(validate())
		    add_topic_form.submit();
	    }
	});
	add_topic_form.addEventListener('submit', function(ev) {
	    if(!validate())
		ev.preventDefault();
	});
    }
    if(query('#add_post_form')) {
	let content = add_post_form.querySelector('[name="content"]');
	let validate = function() {
	    if(!content.value) {
		alert(_('Content cannot be empty.'));
		return false;
	    } else {
		return true;
	    }
	};
	content.addEventListener('keyup', function(ev) {
	    if(ev.key == 'Enter' && ev.ctrlKey) {
		ev.preventDefault();
		if(validate())
		    add_post_form.submit();
	    }
	});
	add_post_form.addEventListener('submit', function(ev) {
	    if(!validate())
		ev.preventDefault();
	});
    }
}


window.addEventListener('load', init_datetime_timer);
window.addEventListener('load', init_tag_selector);
window.addEventListener('load', init_forms);
