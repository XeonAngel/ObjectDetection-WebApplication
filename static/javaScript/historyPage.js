$(document).ready(function () {

    const date_input = $('input[name="date"]');
    const options = {
        format: "dd/mm/yyyy",
        weekStart: 1,
        todayBtn: "linked",
        clearBtn: true,
        orientation: "bottom auto",
        autoclose: true,
        todayHighlight: true

    };
    date_input.datepicker(options);


    $('#searchClass').keypress(function (e) {
        if (e.which == 13) {//Enter key pressed
            e.preventDefault();
            const classToFind = $('#searchClass').val().toLowerCase();
            if (classToFind == '') {
                $('.classList').hide();
                $(".classList:lt(5)").show();
            } else {
                const classList = document.getElementsByClassName('classList');
                let count = 0;
                for (let i = 0; i < classList.length; i++) {
                    let item = classList[i];
                    let value = item.innerText.toLowerCase();
                    let visibility = item.style.display;
                    if (value.indexOf(classToFind) > -1 && count < 5) {
                        count = count + 1;
                        if (visibility == "none") {
                            item.style.display = "block";
                        }
                    } else {
                        if (visibility == "block") {
                            item.style.display = "none";
                        }
                    }
                }
            }
        }
    });

    $('#ClassifiersControlSelect').change(function () {
        const classifier = $(this).val();
        $('#classifierName').val(classifier);

        let req = $.ajax({
            url: '/updateHistoryClasses',
            type: 'POST',
            data: {classifier: classifier}
        })

        req.done(function (data) {
            $("#classesSection").html(data);
        })

    })

});