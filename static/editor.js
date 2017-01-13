var IMAGE_HEADERS = [[137,80,78,71],[255,216],[71,73,70,56]];
var format_checking = false;
var reader = new FileReader();


/**
 * Check if header bytes of a file or a blob matches one of specified formats.
 *
 * @param Blob blob
 * @param Array headers (2d array)
 * @param Function callback
 * @return void
 */
function check_file_format(blob, headers, callback) {
    if(format_checking){
	reader.abort();
	reader = new FileReader();
    }
    format_checking = true;
    reader.addEventListener('loadend', function() {
	var arr = new Uint8Array(reader.result);
	/* valid if one of these formats is matched */
	var ok_outer = false;
	for(let header of headers) {
	    let ok = true;
	    for(let i=0; i<header.length; i++) {
		if(!arr[i] || arr[i] != header[i]) {
		    ok = false;
		    break;
		}
	    }
	    if(ok) {
		ok_outer = true;
		break;
	    }
	}
	callback(ok_outer);
	format_checking = false;
    });
    reader.addEventListener('error', function() {
	callback(false);
	format_checking = false;
    });
    var segment = blob.slice(0, 100);
    reader.readAsArrayBuffer(segment);
}


/**
 * Process and replace selected text in a textarea
 *
 * @param Object textarea
 * @param Function process_function
 * @return void
 */
function replace_text(textarea, process_function) {
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;
    var text = textarea.value;
    var result = process_function(text.slice(start, end));
    var processed = result.processed;
    var delta = result.delta;
    textarea.value = (
	text.slice(0, start) + processed + text.slice(end, text.length)
    );
    textarea.selectionStart = (
	textarea.selectionEnd = start + processed.length + delta
    );
    textarea.focus();
}


/**
 * Insert `text` to the cursor position of `textarea`
 *
 * @param Object textarea
 * @param String text
 * @return void
 */
function insert_text(textarea, text) {
    var position;
    if(textarea.selectionDirection == 'forward')
	position = textarea.selectionStart;
    else
	position = textarea.selectionEnd;
    textarea.value = (
	textarea.value.slice(0, position)
	    + text
	    + textarea.value.slice(
		position, textarea.value.length
	    )
    );
    textarea.selectionStart = textarea.selectionEnd = position + text.length;
}


/**
 * Return a text process function with `prefix` and `suffix` added
 *
 * @param String prefix
 * @param String suffix
 * @return Function
 */
function process_text(prefix, suffix) {
    return function(text) {
	var delta;
	if(text.length > 0)
	    delta = 0;
	else
	    delta = -1*suffix.length;
	return ({
	    processed: prefix + text + suffix,
	    delta: delta
	});
    };
}


/**
 * Initialize specified editor toolbar and textarea
 *
 * @param Object toolbar
 * @param Object textarea
 * @return void
 */
function init_editor_toolbar(toolbar, textarea) {
    var info = JSON.parse(richtext_info.innerHTML);
    /* Formats */
    var formats = info.formats;
    for(let I of formats) {
	let query = printf('.%1_btn', I[0]);
	let prefix = I[1];
	let suffix = I[2];
	var btn = toolbar.querySelector(query);
	cancel_link(btn);
	btn.addEventListener(
	    'click',
	    () => replace_text(textarea, process_text(prefix, suffix))
	);
    }
    /* Code */
    var code_btn = toolbar.querySelector('.code_btn');
    var wrapper = insert_code_dialog_wrapper;
    var code_textarea = insert_code_textarea;
    var lang_input = insert_code_lang_input;
    function open_code_dialog() {
	wrapper.style.display = '';
    }
    function insert_code() {
	insert_text(
	    textarea,
	    printf(
		'\n%1 %2\n%3\n%4\n',
		info.code_prefix,
		lang_input.value,
		code_textarea.value,
		info.code_suffix
	    )
	);
    }
    function close_code_dialog() {
	code_textarea.value = '';
	lang_input.value = '';
	wrapper.style.display = 'none';
	textarea.focus();
    }
    cancel_link(code_btn);
    code_btn.addEventListener('click', open_code_dialog);    
    insert_code_ok_btn.addEventListener('click', function() {
	insert_code();
	close_code_dialog();
    });
    insert_code_cancel_btn.addEventListener('click', close_code_dialog);
    /* Image */
    var image_upload_request;
    var format_available = true;
    function toggle_uploading(is_uploading) {
	if(is_uploading) {
	    insert_image_upload_button.textContent = _('Uploading...');
	    insert_image_upload_button.disabled = true;
	} else {
	    insert_image_upload_button.textContent = _('Insert');
	    insert_image_upload_button.disabled = false;
	}
    }
    function open_image_dialog() {
	insert_image_dialog_wrapper.style.display = '';
    }
    function close_image_dialog() {
	if(image_upload_request) {
	    if(
		image_upload_request.readyState != 0
		&& image_upload_request.readyState != 4
	    )
		image_upload_request.abort();	    
	}
	toggle_uploading(false);
	insert_image_dialog_wrapper.style.display = 'none';
	textarea.focus();
    }
    function upload_ok(xhr) {
	var result = JSON.parse(xhr.responseText);
	if(result.code == 0) {
	    insert_text(
		textarea,
		printf(' %1%2 ', info.image_prefix, result.sha256.slice(0,8))
	    );
	    close_image_dialog();
	} else {
	    alert(printf(_('Failed to upload image: %1'), result.msg));
	    toggle_uploading(false);
	}
    }
    function upload_err(status, text) {
	if(status != 0)
	    alert(
		printf(_('Failed to upload image: %1 %2'), status, text)
	    );
	else
	    alert(
		_('Failed to upload image. Please check if your file is too large or you are offline.')
	    );
	toggle_uploading(false);
    }
    function upload_image() {
	if(!format_available) {
	    alert(_('Error: Invalid file format.'));
	    return;
	}
	toggle_uploading(true);
	image_upload_request = POST(
	    '/image/upload?json=json',
	    new FormData(insert_image_form),
	    upload_ok,
	    upload_err
	);
    }
    var image_btn = toolbar.querySelector('.image_btn');
    cancel_link(image_btn);
    image_btn.addEventListener('click', open_image_dialog);
    insert_image_upload_button.addEventListener('click', upload_image);
    insert_image_cancel_button.addEventListener('click', close_image_dialog);
    insert_image_input.addEventListener('change', function() {
	if(this.files.length > 0)
	    check_file_format(this.files[0], IMAGE_HEADERS, function(ok) {
		if(!ok)
		    format_available = false;
		else
		    format_available = true;
	    });
    });
}


/**
 * Initialize all editor toolbars on the page
 *
 * @return void
 */
function init_editor_toolbars() {
    for(let I of query_all('.editor_toolbar')) {
	let toolbar = I;
	let textarea = toolbar.nextElementSibling;
	init_editor_toolbar(toolbar, textarea);
    }
}


window.addEventListener('load', init_editor_toolbars);
