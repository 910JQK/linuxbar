'use strict';

var WORKER_CODE = "function message(msg) { return function() { postMessage(msg); } }; setInterval(message('update_unread_info'), 150*1000); setInterval(message('update_date'), 60*1000)";
var TITLE_MAX_SIZE = 64;
var CONTENT_MAX_SIZE = 15000;

var messages = {};
var query = function query(selector) {
  return document.querySelector(selector);
};
var query_all = function query_all(selector) {
  return document.querySelectorAll(selector);
};
var timer = new Worker(URL.createObjectURL(new Blob([WORKER_CODE], { type: 'text/javascript' })));

/**
 * Translate message strings
 *
 * @param String str
 * @return String
 */
function _(str) {
  return messages[str] ? messages[str] : str;
}

/**
 * Return the UTF-8 byte count of `str`
 *
 * @param String str
 * @return Number
 */
function utf8size(str) {
  return unescape(encodeURIComponent(str)).length;
}

/**
 * Return a copy of `str` with placeholders replaced by the rest arguments.
 *
 * @param String str
 * @param String ...args
 * @return String
 */
function printf() {
  var str = arguments[0];
  var args = arguments;
  str = str.replace(/%(\d+)|%{(\d+)}/g, function (match, number1, number2) {
    var number = number1 ? number1 : number2;
    return typeof args[number] != 'undefined' ? args[number] : match;
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
  var params = Object.keys(data).map(function (k) {
    return encodeURIComponent(k) + '=' + encodeURIComponent(data[k]);
  }).join('&');
  var xhr = new XMLHttpRequest();
  if (params) url = url + '?' + params;
  xhr.open('GET', url);
  xhr.timeout = timeout ? timeout : 6000;
  xhr.onreadystatechange = function () {
    if (xhr.readyState == 4) {
      if (xhr.status == 200) ok(xhr);else err(xhr.status, xhr.statusText);
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
  if (data instanceof FormData) {
    params = data;
  } else {
    params = Object.keys(data).map(function (k) {
      return encodeURIComponent(k) + '=' + encodeURIComponent(data[k]);
    }).join('&');
  }
  var xhr = new XMLHttpRequest();
  xhr.open('POST', url);
  xhr.timeout = timeout ? timeout : 6000;
  xhr.onreadystatechange = function () {
    if (xhr.readyState == 4) {
      if (xhr.status == 200) ok(xhr);else err(xhr.status, xhr.statusText);
    }
  };
  xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
  if (typeof params == 'string') {
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.setRequestHeader('Content-length', params.length);
  }
  xhr.send(params);
  return xhr;
}

/**
 * Cancel a link so that javascript event can make sense
 *
 * @param Object link
 * @return void
 */
function cancel_link(link) {
  link.href = 'javascript: void(0)';
  link.target = '';
}

/**
 * Format date
 *
 * @param Number timestamp
 * @return String
 */
function format_date(timestamp) {
  /* behaviour of this function must be consistent with the back-end */
  var now = Date.now() / 1000;
  var delta = Math.round(now - timestamp);
  if (delta < 60) {
    return _('just now');
  } else if (delta < 3600) {
    var minutes = Math.floor(delta / 60);
    if (minutes == 1) return _('a minute ago');else return printf(_('%1 minutes ago'), minutes);
  } else if (delta < 86400) {
    var hours = Math.floor(delta / 3600);
    if (hours == 1) return _('an hour ago');else return printf(_('%1 hours ago'), hours);
    /*  604800 = 86400*7  */
  } else if (delta < 604800) {
    var days = Math.floor(delta / 86400);
    if (days == 1) return _('a day ago');else return printf(_('%1 days ago'), days);
    /* 2629746 = 86400*(31+28+97/400+31+30+31+30+31+31+30+31+30+31)/12 */
  } else if (delta < 2629746) {
    var weeks = Math.floor(delta / 604800);
    if (weeks == 1) return _('a week ago');else return printf(_('%1 weeks ago'), weeks);
    /* 31556952 = 86400*(365+97/400) */
  } else if (delta < 31556952) {
    var months = Math.floor(delta / 2629746);
    if (months == 1) return _('a month ago');else return printf(_('%1 months ago'), months);
  } else {
    var years = Math.floor(delta / 31556952);
    if (years == 1) return _('a year ago');else return printf(_('%1 years ago'), years);
  }
}

/**
 * Update unread count info in user toolbar
 *
 * @return void
 */
function update_unread_info() {
  if (!query('#link_notify_reply')) return;
  GET('/user/unread-info', {}, function (xhr) {
    function try_to_highlight(link, n) {
      if (n > 0 && !link.classList.contains('link_highlight')) link.classList.add('link_highlight');else if (n == 0 && link.classList.contains('link_highlight')) link.classList.remove('link_highlight');
    }
    var result = JSON.parse(xhr.responseText);
    var total = 0;
    var _iteratorNormalCompletion = true;
    var _didIteratorError = false;
    var _iteratorError = undefined;

    try {
      for (var _iterator = Object.keys(result)[Symbol.iterator](), _step; !(_iteratorNormalCompletion = (_step = _iterator.next()).done); _iteratorNormalCompletion = true) {
        var item = _step.value;

        var link = query(printf('#link_notify_%1', item));
        var n = result[item];
        link.textContent = printf('%1(%2)', link.dataset.content, n);
        try_to_highlight(link, n);
        total += n;
      }
    } catch (err) {
      _didIteratorError = true;
      _iteratorError = err;
    } finally {
      try {
        if (!_iteratorNormalCompletion && _iterator.return) {
          _iterator.return();
        }
      } finally {
        if (_didIteratorError) {
          throw _iteratorError;
        }
      }
    }

    link_notify_all.firstElementChild.innerText = total.toString();
    try_to_highlight(link_notify_all, total);
  }, function (status, text) {
    console.error(printf('Failed to get unread count: %1 %2', status, text));
  });
}

/**
 * Update relative datetime of all date spans on the page
 *
 * @return void
 */
function update_date() {
  var _iteratorNormalCompletion2 = true;
  var _didIteratorError2 = false;
  var _iteratorError2 = undefined;

  try {
    for (var _iterator2 = query_all('.date')[Symbol.iterator](), _step2; !(_iteratorNormalCompletion2 = (_step2 = _iterator2.next()).done); _iteratorNormalCompletion2 = true) {
      var span = _step2.value;

      span.textContent = format_date(span.dataset.ts);
    }
  } catch (err) {
    _didIteratorError2 = true;
    _iteratorError2 = err;
  } finally {
    try {
      if (!_iteratorNormalCompletion2 && _iterator2.return) {
        _iterator2.return();
      }
    } finally {
      if (_didIteratorError2) {
        throw _iteratorError2;
      }
    }
  }

  var _iteratorNormalCompletion3 = true;
  var _didIteratorError3 = false;
  var _iteratorError3 = undefined;

  try {
    for (var _iterator3 = query_all('.edited_mark')[Symbol.iterator](), _step3; !(_iteratorNormalCompletion3 = (_step3 = _iterator3.next()).done); _iteratorNormalCompletion3 = true) {
      var mark = _step3.value;

      mark.title = format_date(mark.dataset.ts);
    }
  } catch (err) {
    _didIteratorError3 = true;
    _iteratorError3 = err;
  } finally {
    try {
      if (!_iteratorNormalCompletion3 && _iterator3.return) {
        _iterator3.return();
      }
    } finally {
      if (_didIteratorError3) {
        throw _iteratorError3;
      }
    }
  }
}

/**
 * Enable the timer to update unread info
 *
 * @return void
 */
function init_unread_info_timer() {
  timer.addEventListener('message', function (ev) {
    if (ev.data == 'update_unread_info') {
      if (!document.hidden) {
        // only check when the page is foreground
        update_unread_info();
      }
    }
  });
}

/**
 * Enable the timer to update relative datetime
 *
 * @return void
 */
function init_datetime_timer() {
  timer.addEventListener('message', function (ev) {
    if (ev.data == 'update_date') update_date();
  });
}

/**
 * Initialize the tag selector
 *
 * @return void
 */
function init_tag_selector() {
  if (query('#tag_selector')) {
    var fieldset = query('#add_topic_form > fieldset');
    var banned = fieldset && fieldset.disabled;
    var tags_input = query('select[name="tags"]');

    var _loop = function _loop(I) {
      var option = I;
      var checkbox = tag_selector.querySelector(printf('input[data-slug="%1"]', option.value));
      var event_handler = function event_handler() {
        option.selected = this.checked;
      };
      checkbox.addEventListener('change', event_handler);
      event_handler.call(checkbox);
      if (!banned) {
        checkbox.parentElement.addEventListener('click', function (ev) {
          if (ev.target != checkbox) {
            checkbox.checked = !checkbox.checked;
            event_handler.call(checkbox);
          }
        });
      } else {
        checkbox.parentElement.style.color = 'gray';
      }
      checkbox.nextElementSibling.unselectable = 'on';
      checkbox.nextElementSibling.onselectstart = function () {
        return false;
      };
    };

    var _iteratorNormalCompletion4 = true;
    var _didIteratorError4 = false;
    var _iteratorError4 = undefined;

    try {
      for (var _iterator4 = tags_input.options[Symbol.iterator](), _step4; !(_iteratorNormalCompletion4 = (_step4 = _iterator4.next()).done); _iteratorNormalCompletion4 = true) {
        var I = _step4.value;

        _loop(I);
      }
    } catch (err) {
      _didIteratorError4 = true;
      _iteratorError4 = err;
    } finally {
      try {
        if (!_iteratorNormalCompletion4 && _iterator4.return) {
          _iterator4.return();
        }
      } finally {
        if (_didIteratorError4) {
          throw _iteratorError4;
        }
      }
    }

    tags_input.style.display = 'none';
    tag_selector.style.display = '';
  }
}

/**
 * Add addtional features to forms
 *
 * @return void
 */
function init_forms() {
  if (query('#add_topic_form')) {
    var title = add_topic_form.querySelector('[name="title"]');
    var content = add_topic_form.querySelector('[name="content"]');
    var validate = function validate() {
      if (!title.value) {
        alert(_('Title cannot be empty.'));
      } else if (!content.value) {
        alert(_('Content cannot be empty.'));
      } else if (utf8size(title.value) > TITLE_MAX_SIZE) {
        alert(printf(_('Title cannot exceed %1 bytes.'), TITLE_MAX_SIZE));
      } else if (utf8size(content.value) > CONTENT_MAX_SIZE) {
        alert(printf(_('Content cannot exceed %1 bytes'), CONTENT_MAX_SIZE));
      } else {
        return true;
      }
      return false;
    };
    content.addEventListener('keyup', function (ev) {
      if (ev.key == 'Enter' && ev.ctrlKey) {
        ev.preventDefault();
        if (validate()) add_topic_form.submit();
      }
    });
    add_topic_form.addEventListener('submit', function (ev) {
      if (!validate()) ev.preventDefault();
    });
  }
  if (query('#add_post_form')) {
    var _content = add_post_form.querySelector('[name="content"]');
    var _validate = function _validate() {
      if (!_content.value) {
        alert(_('Content cannot be empty.'));
      } else if (utf8size(_content.value) > CONTENT_MAX_SIZE) {
        alert(printf(_('Content cannot exceed %1 bytes'), CONTENT_MAX_SIZE));
      } else {
        return true;
      }
      return false;
    };
    _content.addEventListener('keyup', function (ev) {
      if (ev.key == 'Enter' && ev.ctrlKey) {
        ev.preventDefault();
        if (_validate()) add_post_form.submit();
      }
    });
    add_post_form.addEventListener('submit', function (ev) {
      if (!_validate()) ev.preventDefault();
    });
  }
}

/**
 * Expand clickable area of items of topic list
 *
 * @return void
 */
function init_topic_links() {
  var _loop2 = function _loop2(I) {
    var url = I.querySelector('.title > a').href;
    I.addEventListener('click', function (ev) {
      if (document.body.offsetWidth <= 1000 && !ev.target.classList.contains('tag_link') && !ev.target.classList.contains('summary_image')) {
        ev.preventDefault();
        window.open(url);
      }
    });
  };

  var _iteratorNormalCompletion5 = true;
  var _didIteratorError5 = false;
  var _iteratorError5 = undefined;

  try {
    for (var _iterator5 = query_all('.topic')[Symbol.iterator](), _step5; !(_iteratorNormalCompletion5 = (_step5 = _iterator5.next()).done); _iteratorNormalCompletion5 = true) {
      var I = _step5.value;

      _loop2(I);
    }
  } catch (err) {
    _didIteratorError5 = true;
    _iteratorError5 = err;
  } finally {
    try {
      if (!_iteratorNormalCompletion5 && _iterator5.return) {
        _iterator5.return();
      }
    } finally {
      if (_didIteratorError5) {
        throw _iteratorError5;
      }
    }
  }
}

/**
 * Initialize translations of front-end
 *
 * @return void
 */
function init_translation() {
  if (query('#translation_data')) {
    var messages_dict = JSON.parse(translation_data.innerHTML);
    if (messages_dict) {
      messages = messages_dict;
    }
  }
}

window.addEventListener('load', init_datetime_timer);
window.addEventListener('load', init_forms);
window.addEventListener('load', init_tag_selector);
window.addEventListener('load', init_topic_links);
window.addEventListener('load', init_translation);