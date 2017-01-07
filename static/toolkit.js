var query = selector => document.querySelector(selector);
var query_all = selector => document.querySelectorAll(selector);


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


function update_unread_count() {
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


function init_timer() {
    var timer = new Worker('/static/timer.js');
    timer.addEventListener('message', function(ev) {
	update_unread_count();
    });
}
