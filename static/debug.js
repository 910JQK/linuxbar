function postAjax(url, data, success) {
    var params = typeof data == 'string' ? data : Object.keys(data).map(
	function(k){ return encodeURIComponent(k) + '=' + encodeURIComponent(data[k]) }
    ).join('&');

    var xhr = new XMLHttpRequest()
    xhr.open('POST', url);
    xhr.onreadystatechange = function() {
	if (xhr.readyState>3 && xhr.status==200) { success(xhr.responseText); }
    };
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.setRequestHeader('Content-length', params.length);
    xhr.send(params);
    return xhr;
}
