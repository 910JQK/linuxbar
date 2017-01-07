function message(msg) {
    return function() {
	postMessage(msg);
    }
}


setInterval(message('update_unread_info'), 150*1000);
