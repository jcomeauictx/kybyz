if (typeof(com) == "undefined") com = {};
com.kybyz = {};
com.kybyz.app = {};
com.kybyz.app.UpdateInterval = 60000;  // milliseconds, start off slow
com.kybyz.app.getDataName = function(string) {
    const offset = string.indexOf("-");
    return string.substring(offset + 1);
};

com.kybyz.app.updatePage = function() {
    const cka = com.kybyz.app;
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
        if (xhr.readyState == 4) {
            console.log("result of updateCheck XHR: " + xhr.response);
            if (xhr.response == contentHash) {
                console.log("same content as last check");
            } else {
                /* new content */
                oldContent.parentNode.replaceChild(
                    xhr.response.documentElement, oldContent);
            }
        } else {
            console.log("xhr.readyState: " + xhr.readyState);
        }
    };
    xhr.responseType = "document";
    xhr.send("name=" + cka.getDataName(elementId) + "&hash=" + contentHash);
};

window.addEventListener("load", function(event) {
    const cka = com.kybyz.app;
    const warning = document.getElementById("kbz-js-warning");
    const text = warning.childNodes[0];
    let fixed = "INFO:found compatible javascript";
    const offset = text.data.indexOf("ERROR");
    fixed = text.data.substring(0, offset) + fixed;
    warning.replaceChild(document.createTextNode(fixed), text);
    window.setInterval(cka.updatePage, cka.UpdateInterval);
});
// vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
