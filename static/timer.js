const INTERVAL_UPDATE_DATE = 60*1000;


function message(msg) {
    return function() {
	postMessage(msg);
    }
}


setInterval(message('update_date'), INTERVAL_UPDATE_DATE);
