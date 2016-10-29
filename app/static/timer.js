const INTERVAL_UPDATE_DATE = 60*1000;
const INTERVAL_UPDATE_UNREAD_COUNT = 150*1000;


function message(msg) {
    return function() {
	postMessage(msg);
    }
}


setInterval(message('update_date'), INTERVAL_UPDATE_DATE);
setInterval(message('update_unread_count'), INTERVAL_UPDATE_UNREAD_COUNT);
