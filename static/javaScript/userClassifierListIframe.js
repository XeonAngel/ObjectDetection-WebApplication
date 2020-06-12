function myFunction(classToFind) {
    str1 = '/classesforclassifier/';
    var newUri = str1.concat(classToFind);
    $('#classListID').attr("src", newUri);
}