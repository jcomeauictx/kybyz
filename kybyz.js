if (typeof(com) == "undefined") com = {};
com.kybyz = {};
com.kybyz.app = {};
com.kybyz.app.UpdateInterval = 1000;  // milliseconds, start off slow
com.kybyz.app.getDataName = function(string) {
    const offset = string.indexOf("-");
    return string.substring(offset + 1);
};

com.kybyz.app.updatePage = function() {
    const cka = com.kybyz.app;
    //cka.updateCheck("kbz-posts");
    cka.updateCheck("kbz-messages");
};

com.kybyz.app.updateCheck = function(elementId) {
    const cka = com.kybyz.app;
    let xhr, contentHash;
    if (window.XMLHttpRequest) xhr = new XMLHttpRequest();
    else xhr = new ActiveXObject("Microsoft.XMLHTTP");
    xhr.open("POST", "/update/", true);
    xhr.setRequestHeader('Content-Type',
                         'application/x-www-form-urlencoded');
    oldContent = document.getElementById(elementId);
    contentHash = oldContent.getAttribute("data-version");
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            console.log("result of updateCheck XHR:", xhr.response);
            /* new content */
            oldContent.replaceWith(xhr.response.body.firstChild);
        } else {
            console.log("xhr.readyState:", xhr.readyState,
                        ", xhr.status: ", xhr.status);
        }
    };
    xhr.responseType = "document";
    /* NOTE: when you receive a "document" from the backend, even a simple
     * <div>some text</div> gets turned into a full #document.
     * xml.response.documentElement will be the html element, which contains
     * the head, body, and finally the div.
     */
    xhr.send("name=" + cka.getDataName(elementId) + "&hash=" + contentHash);
};

window.addEventListener("load", function(event) {
    const cka = com.kybyz.app;
    const warning = document.getElementById("kbz-js-warning");
    const text = warning.childNodes[0];
    // NOTE: keep this following string identical to that in kybyz.py
    let fixed = "INFO:found compatible javascript engine";
    const offset = text.data.indexOf(":") + 1;
    fixed = text.data.substring(0, offset) + fixed;
    warning.replaceChild(document.createTextNode(fixed), text);
    //window.setInterval(cka.updatePage, cka.UpdateInterval);
});
// vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
