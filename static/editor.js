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
