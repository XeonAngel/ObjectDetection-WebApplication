$(document).ready(function () {
    const header = document.getElementById("button-groupID");
    const btns = header.getElementsByClassName("button");
    for (let i = 0; i < btns.length; i++) {
        btns[i].addEventListener("click", function () {
            $('#uploadDataDiv').toggle();
            $('#analyzeDiv').toggle();
            const current = document.getElementsByClassName("active");
            current[0].className = current[0].className.replace(" active", "");
            this.className += " active";
        });
    }

    $(".dropdown-menu li a").click(function () {
        $(".dropdown-toggle").text($(this).text());
        $('.dropdownItem.active').removeClass('active')
        $(this).parent().addClass('active')
    });

});


// Get a reference to the progress bar, wrapper & status label
const progress = document.getElementById("uploadProgressBar");
const progress_wrapper = document.getElementById("uploadData_progress_wrapper");
// Get a reference to the 3 buttons
const upload_btn = document.getElementById("upload_btn");
const cancel_btn = document.getElementById("uploadData_cancel_btn");
// Get a reference to the alert wrapper
const alert_wrapper = document.getElementById("uploadData_alert_wrapper");
// Get a reference to the file input element & input label
const input = document.getElementById("file_input");
const file_input_label = document.getElementById("file_input_label");
const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg'];

function show_alert(message, alert, alert_wrapper_dest) {
    alert_wrapper_dest.innerHTML = `
    <div id="alert" class="alert alert-${alert} alert-dismissible fade show" role="alert">
      <span>${message}</span>
      <button type="button" class="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
  `
}

// Function to upload file
function uploadData(url) {
    // Reject if the file input is empty & throw alert
    if (!input.value) {
        show_alert("No file selected", "warning", alert_wrapper)
        return;
    }

    // Create a new FormData instance
    const data = new FormData();

    // Create a XMLHTTPRequest instance
    const request = new XMLHttpRequest();

    // Set the response type
    request.responseType = "json";

    // Clear any existing alerts
    alert_wrapper.innerHTML = "";

    // Disable the input during upload
    input.disabled = true;

    // Hide the upload button
    upload_btn.classList.add("d-none");

    // Show the cancel button
    cancel_btn.classList.remove("invisible");

    // Show the progress bar
    progress_wrapper.classList.remove("invisible");

    // Get a reference to the file
    const file = input.files[0];
    const fileType = file.type;
    if (!allowedTypes.includes(fileType)) {
        show_alert("Please select a valid file (JPEG/JPG/PNG).", "warning", alert_wrapper);
        reset();
        return false;
    }

    // Get a reference to the filename
    const filename = file.name;

    // Get a reference to the filesize & set a cookie
    const filesize = file.size;
    document.cookie = `filesize=${filesize}`;

    // Append the file to the FormData instance
    data.append("file", file);

    // request progress handler
    request.upload.addEventListener("progress", function (e) {

        // Get the loaded amount and total filesize (bytes)
        const loaded = e.loaded;
        const total = e.total;

        // Calculate percent uploaded
        const percent_complete = (loaded / total) * 100;

        // Update the progress text and progress bar
        progress.setAttribute("style", `width: ${Math.floor(percent_complete)}%`);
        // progress_status.innerText = `${Math.floor(percent_complete)}% uploaded`;

        progress.innerText = `${Math.floor(percent_complete)}% uploaded`;
    })

    // request load handler (transfer complete)
    request.addEventListener("load", function (e) {
        if (request.status == 200) {
            show_alert(`${request.response.message}`, "success", alert_wrapper);
        } else {
            show_alert(`Error uploading file`, "danger", alert_wrapper);
        }
        reset();
    });

    // request error handler
    request.addEventListener("error", function (e) {

        reset();
        show_alert(`Error uploading file`, "warning", alert_wrapper);

    });

    // request abort handler
    request.addEventListener("abort", function (e) {
        reset();
        show_alert(`Upload cancelled`, "primary", alert_wrapper);
    });

    // Open and send the request
    request.open("post", url);
    request.send(data);

    cancel_btn.addEventListener("click", function () {
        request.abort();
    })

}

// Function to update the input placeholder
function input_filename() {
    file_input_label.innerText = input.files[0].name;
}

// Function to reset the page
function reset() {
    // Clear the input
    input.value = null;

    // Hide the cancel button
    cancel_btn.classList.add("invisible");

    // Reset the input element
    input.disabled = false;

    // Show the upload button
    upload_btn.classList.remove("d-none");

    // Hide the loading button
    // loading_btn.classList.add("d-none");

    // Hide the progress bar
    progress_wrapper.classList.add("invisible");

    // Reset the progress bar state
    progress.setAttribute("style", `width: 0%`);

    // Reset the input placeholder
    file_input_label.innerText = "Select file";
}


// Get a reference to the progress bar, wrapper & status label
const analyze_progress = document.getElementById("analyzeData_progressbar");
const analyze_progress_wrapper = document.getElementById("analyzeData_progress_wrapper");
// Get a reference to the 3 buttons
const analyze_btn = document.getElementById("analyze_btn");
const analyze_dropdown_btn = document.getElementById("dropdown_button");
const analyze_stop_btn = document.getElementById("analyzeStop_btn");
const analyze_result_btn = document.getElementById("result_btn");
// Get a reference to the alert wrapper
const analyze_alert_wrapper = document.getElementById("analyzeData_alert_wrapper");

// Function to upload file
function analyzeData(url) {
    // Create a new FormData instance
    const data = analyze_dropdown_btn.innerText;

    // Create a XMLHTTPRequest instance
    const request = new XMLHttpRequest();

    // Set the response type
    request.responseType = "json";

    // Clear any existing alerts
    analyze_alert_wrapper.innerHTML = "";

    // Hide the upload button
    analyze_btn.classList.add("d-none");

    // Show the cancel button
    analyze_stop_btn.classList.remove("invisible");

    // Show the progress bar
    analyze_progress_wrapper.classList.remove("invisible");

    // request load handler (transfer complete)
    request.addEventListener("load", function (e) {
        if (request.status == 200) {
            show_alert(`${request.response.message}`, "success", analyze_alert_wrapper);
        } else {
            show_alert(`Error starting the analyze`, "danger", analyze_alert_wrapper);
        }
    });
    // Open and send the request
    request.open("post", url);
    request.send(data);
    setInterval(getProgress, 1000)
}

function getProgress() {
    $.ajax({
        url: '/getDetectionProgress',
        type: 'post',
        success: function (response) {
            // Perform operation on the return value
            // alert(response);
            analyze_progress.setAttribute("style", `width: ${Math.floor(response.message)}%`);
            // progress_status.innerText = `${Math.floor(percent_complete)}% uploaded`;

            analyze_progress.innerText = `${Math.floor(response.message)}% uploaded`;
        }
    });
}

function stopDetectionScript(url) {
    $.ajax({
        url: url,
        type: 'post',
        success: function (response) {
            // Perform operation on the return value
            show_alert(`${response.message}`, "warning", analyze_alert_wrapper);
        }
    });
}