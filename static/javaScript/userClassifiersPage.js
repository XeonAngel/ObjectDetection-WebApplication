$('document').ready(function () {

    $('#searchClass').keypress(function (e) {
        if (e.which == 13) {//Enter key pressed
            var classToFind = $('#searchClass').val();
            if (classToFind == '') {
                $('#classifierListId').attr("src", "/userclassifierslist/all");
            } else {
                str1 = "/userclassifierslist/";
                var newUri = str1.concat(classToFind);
                $('#classifierListId').attr("src", newUri);
            }
        }
    });

});