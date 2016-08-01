function GET(url, data, ok, err) {
    var params = Object.keys(data).map(
	k => encodeURIComponent(k) + '=' + encodeURIComponent(data[k])
    ).join('&');
    var xhr = new XMLHttpRequest();
    if(params)
	url = url + '?' + params;
    xhr.open('GET', url);
    xhr.onreadystatechange = function() {
	if(xhr.readyState == 4) {
	    if(xhr.status==200)
		ok(xhr);
	    else
		err(xhr);
	}
    };
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.send();
    return xhr;
}


function POST(url, data, ok, err) {
    var params = Object.keys(data).map(
	k => encodeURIComponent(k) + '=' + encodeURIComponent(data[k])
    ).join('&');
    var xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    xhr.onreadystatechange = function() {
	if(xhr.readyState == 4) {
	    if(xhr.status==200)
		ok(xhr);
	    else
		err(xhr);
	}
    };
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.setRequestHeader('Content-length', params.length);
    xhr.send(params);
    return xhr;
}
