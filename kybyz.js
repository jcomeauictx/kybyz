if (typeof(com) == "undefined") com = {};
com.kybyz = {};
com.kybyz.app = {};
window.addEventListener("load", function(event) {
    const warning = document.getElementById("kbz-js-warning");
    const text = warning.childNodes[0];
    let fixed = "INFO:found compatible javascript";
    const offset = text.data.indexOf("ERROR");
    fixed = text.data.substring(0, offset) + fixed;
    warning.replaceChild(document.createTextNode(fixed), text);
});
