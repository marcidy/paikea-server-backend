function sanitize(string) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        "/": '&#x2F;',
    };
    const reg = /[&<>"'/]/ig;
    return string.replace(reg, (match) => (map[match]));
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function log(level, msg) {
    $("#messages").append('<div class="' + level +'">' + sanitize(msg) + '</div>');
    $("#messages").scrollTop($("#messages")[0].scrollHeight);
}

export { sanitize, delay, log };
