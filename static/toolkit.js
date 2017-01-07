var query = selector => document.querySelector(selector);
var query_all = selector => document.querySelectorAll(selector);
var _ = str => str; // reserved for l10n
var timer = new Worker('/static/timer.js');


/**
 * Return a copy of `str` with placeholders replaced by the rest arguments.
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


function update_unread_info() {
    if(!query('#link_notify_reply'))
	return;
    GET(
	'/user/unread-info',
	{},
	function(xhr) {
	    var result = JSON.parse(xhr.responseText);
	    for(let item of Object.keys(result)) {
		let link = query(printf('#link_notify_%1', item));
		link.textContent = (
		    printf('%1(%2)', link.dataset.content, result[item])
		);
	    }
	},
	function(status, text) {
	    console.error(
		printf('Failed to get unread count: %1 %2', status, text)
	    );
	}
    );
}


function update_date() {
    for(let span of query_all('.date')) {
	span.textContent = format_date(span.dataset.ts);
    }
}


function init_unread_info_timer() {
    timer.addEventListener('message', function(ev) {
	if(ev.data == 'update_unread_info')
	    update_unread_info();
    });
}


function init_datetime_timer() {
    timer.addEventListener('message', function(ev) {
	if(ev.data == 'update_date')
	    update_date();
    });
}


window.addEventListener('load', init_datetime_timer);
