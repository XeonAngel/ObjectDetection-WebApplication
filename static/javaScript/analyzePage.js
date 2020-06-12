$(document).ready(function () {

    var header = document.getElementById("button-groupID");
    var btns = header.getElementsByClassName("button");
    for (var i = 0; i < btns.length; i++) {
        btns[i].addEventListener("click", function () {
            $('#uploadDataDiv').toggle();
            $('#analyzeDiv').toggle();
            var current = document.getElementsByClassName("active");
            current[0].className = current[0].className.replace(" active", "");
            this.className += " active";
        });
    }
});