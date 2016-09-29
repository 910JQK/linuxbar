var query = selector => document.querySelector(selector);
var query_all = selector => document.querySelectorAll(selector);


var timer;


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
 * Simplified version of Date.prototype.toISOString()
 *
 * @param Number timestamp
 * @return String
 */
function iso_date(timestamp) {
    var date = new Date(timestamp*1000);
    function pad(num) {
	if (num < 10) {
	    return '0' + num;
	}
	return String(num);
    }
    return (
	date.getFullYear() +
	    '-' + pad(date.getMonth() + 1) +
	    '-' + pad(date.getDate()) +
	    ' ' + pad(date.getHours()) +
	    ':' + pad(date.getMinutes()) +
	    ':' + pad(date.getSeconds())
    );
}


/**
 * Format date
 *
 * @param Number timestamp
 * @param Boolean detailed = False
 * @return String
 */
function format_date(timestamp, detailed) {
    /* behaviour of this function must be consistent with the back-end */
    if(detailed)
	return iso_date(timestamp);
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
 * Update all the date strings on the page
 *
 * @return void
 */
function update_date() {
    for(let element of query_all('.date'))
	element.textContent = format_date(element.dataset.ts);
}


/**
 * Update unread notification count
 *
 * @return void
 */
function update_unread_count() {
    GET(
	'/api/user/info/unread',
	{},
	function(xhr) {
	    var result = JSON.parse(xhr.responseText)
	    if(result.code == 0) {
		replyme_link.textContent = printf(
		    '%1(%2)',
		    replyme_link.dataset.content,
		    result.data['reply']
		);
		atme_link.textContent = printf(
		    '%1(%2)',
		    atme_link.dataset.content,
		    result.data['at']
		);
	    } else {
		console.error(
		    printf('Failed to get unread count: %1', result.msg)
		);
	    }
	},
	function(status, text) {
	    console.error(
		printf('Failed to get unread count: %1 %2', status, text)
	    );
	}
    )
}


/**
 * Load timer in another thread
 * @param Object items
 *
 * @return void
 */
function init_timer(items) {
    if(!items)
	items = {date: true, unread_count: false};
    timer = new Worker('/static/timer.js');
    timer.addEventListener('message', function(ev) {
	if(ev.data == 'update_date' && items['date'])
	    update_date();
	if(ev.data == 'update_unread_count' && items['unread_count'])
	    update_unread_count();
    });
}


/**
 * Scroll to anchor without changing the hash in the URL
 *
 * @param String anchor
 * @return void
 */
function scroll_to(anchor) {
    var node = query(anchor);
    var top = 0;
    while(node) {
	top += node.offsetTop;
	node = node.offsetParent;
    }
    document.documentElement.scrollTop = top;
}
