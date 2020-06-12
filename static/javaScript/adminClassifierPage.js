   $("[type=checkbox]").on("click", function () {
           if ($(this).prop("checked")) {
               $(this).parent().attr("aria-checked", "true");
           } else {
               $(this).parent().attr("aria-checked", "false");
           }
       });