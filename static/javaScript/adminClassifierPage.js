$('document').ready(function () {
    $('#searchClassifier').keypress(function (e) {
        if (e.which == 13) {//Enter key pressed
            const classifierToFind = $('#searchClassifier').val();
            let req = $.ajax({
                url: '/updateClassifierList',
                type: 'POST',
                data: {classifier: classifierToFind}
            })
            req.done(function (data) {
                $("#classifierSection").html(data);
            })
        }
    });

    $(document).on('click', '#ClassesDivButton', function () {
        if (document.getElementById("ClassesDiv").classList.contains('d-none')) {
            document.getElementById("ClassesDiv").classList.remove('d-none');
            if (document.getElementById("DetailsDiv").classList.contains('d-none')) {
                document.getElementById("TrainDiv").classList.add('d-none');
            } else {
                document.getElementById("DetailsDiv").classList.add('d-none');
            }
        }
    });
    $(document).on('click', '#DetailsDivButton', function () {
        if (document.getElementById("DetailsDiv").classList.contains('d-none')) {
            document.getElementById("DetailsDiv").classList.remove('d-none');
            if (document.getElementById("ClassesDiv").classList.contains('d-none')) {
                document.getElementById("TrainDiv").classList.add('d-none');
            } else {
                document.getElementById("ClassesDiv").classList.add('d-none');
            }
        }
    });
    $(document).on('click', '#TrainDivButton', function () {
        if (document.getElementById("TrainDiv").classList.contains('d-none')) {
            document.getElementById("TrainDiv").classList.remove('d-none');
            if (document.getElementById("DetailsDiv").classList.contains('d-none')) {
                document.getElementById("ClassesDiv").classList.add('d-none');
            } else {
                document.getElementById("DetailsDiv").classList.add('d-none');
            }
        }
    });

});

function showDetails(classifier) {
    let req = $.ajax({
        url: '/showClassifierDetails',
        type: 'POST',
        data: {classifier: classifier}
    })
    req.done(function (data) {
        $("#classifierDetailSection").html(data);
        // Get reference to the 3 tab buttons
        detailsDivButton = document.getElementById("DetailsDivButton");
        trainDivButton = document.getElementById("TrainDivButton");
        classesDivButton = document.getElementById("ClassesDivButton");
        // Get a reference to the progress bar, wrapper & status label
        progress = document.getElementById("uploadProgressBar");
        trainProgress = document.getElementById("trainProgressBar");
        progress_wrapper = document.getElementById("uploadData_progress_wrapper");
        train_progress_wrapper = document.getElementById("trainData_progress_wrapper");
        // Get a reference to the 2 buttons
        upload_btn = document.getElementById("upload_btn");
        train_btn_div = document.getElementById("trainButtonsDiv");
        cancel_btn = document.getElementById("uploadData_cancel_btn");
        train_cancel_btn = document.getElementById("trainData_cancel_btn");
        // Get a reference to the alert wrapper
        alert_wrapper = document.getElementById("uploadData_alert_wrapper");
        train_alert_wrapper = document.getElementById("trainData_alert_wrapper");
        // Get a reference to the file input element & input label
        input = document.getElementById("file_input");
        file_input_label = document.getElementById("file_input_label");
        allowedTypes = ['application/vnd.rar', 'application/x-7z-compressed', 'application/zip',
            'application/x-zip-compressed', 'multipart/x-zip', 'application/x-compressed',
            'application/x-rar-compressed', 'application/x-tar'];
    })
}

// Get reference to the 3 tab buttons
let detailsDivButton = document.getElementById("DetailsDivButton");
let trainDivButton = document.getElementById("TrainDivButton");
let classesDivButton = document.getElementById("ClassesDivButton");
// Get a reference to the progress bar, wrapper & status label
let progress = document.getElementById("uploadProgressBar");
let trainProgress = document.getElementById("trainProgressBar");
let progress_wrapper = document.getElementById("uploadData_progress_wrapper");
let train_progress_wrapper = document.getElementById("trainData_progress_wrapper");
// Get a reference to the 2 buttons
let upload_btn = document.getElementById("upload_btn");
let train_btn_div = document.getElementById("trainButtonsDiv");
let cancel_btn = document.getElementById("uploadData_cancel_btn");
let train_cancel_btn = document.getElementById("trainData_cancel_btn");
// Get a reference to the alert wrapper
let alert_wrapper = document.getElementById("uploadData_alert_wrapper");
let train_alert_wrapper = document.getElementById("trainData_alert_wrapper");
// Get a reference to the file input element & input label
let input = document.getElementById("file_input");
let file_input_label = document.getElementById("file_input_label");
let allowedTypes = ['application/vnd.rar', 'application/x-7z-compressed', 'application/zip',
    'application/x-zip-compressed', 'multipart/x-zip', 'application/x-compressed',
    'application/x-rar-compressed', 'application/x-tar'];

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
function uploadData(url, classifier) {
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
        show_alert("Please select a valid file (ZIP/RAR/TAR).", "warning", alert_wrapper);
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
    data.append('classifier', classifier);

    // request progress handler
    request.upload.addEventListener("progress", function (e) {

        // Get the loaded amount and total filesize (bytes)
        const loaded = e.loaded;
        const total = e.total;

        // Calculate percent uploaded
        const percent_complete = (loaded / total) * 100;

        // Update the progress text and progress bar
        progress.setAttribute("style", `width: ${Math.floor(percent_complete)}%`);
        progress.innerText = `${Math.floor(percent_complete)}% uploaded`;
    })

    // request load handler (transfer complete)
    request.addEventListener("load", function (e) {
        if (request.status == 200) {
            show_alert(`${request.response.message}`, "success", alert_wrapper);
            train_btn_div.classList.remove('invisible')
            train_progress_wrapper.classList.remove('invisible')
            train_cancel_btn.classList.remove('invisible')
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

    // Hide the progress bar
    progress_wrapper.classList.add("invisible");

    // Reset the progress bar state
    progress.setAttribute("style", `width: 0%`);

    // Reset the input placeholder
    file_input_label.innerText = "Select file";
}

// Function to upload file
function train(url, classifier, trainingType) {
    // Create a new FormData instance
    const data = new FormData();

    // Create a XMLHTTPRequest instance
    const request = new XMLHttpRequest();

    // Set the response type
    request.responseType = "json";

    // Clear any existing alerts
    alert_wrapper.innerHTML = "";
    train_alert_wrapper.innerHTML = "";

    // Disable the input during upload
    // input.disabled = true;
    document.getElementsByClassName("custom-file")[0].classList.add('d-none');

    // Hide the upload button
    upload_btn.classList.add("d-none");
    train_btn_div.classList.add("d-none");

    // Show the cancel button
    train_cancel_btn.classList.remove("invisible");

    // Show the progress bar
    train_progress_wrapper.classList.remove("invisible");

    // Append the file to the FormData instance
    data.append('classifier', classifier);
    data.append('trainingType', trainingType);

    // request load handler (transfer complete)
    request.addEventListener("load", function (e) {
        if (request.status == 200) {
            show_alert(`${request.response.message}`, "success", train_alert_wrapper);
        } else {
            show_alert(`Error starting training`, "danger", train_alert_wrapper);
        }
        reset();
    });

    // Open and send the request
    request.open("post", url);
    request.send(data);
}