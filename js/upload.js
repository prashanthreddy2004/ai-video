const API_BASE =
"https://50rlwa0agc.execute-api.us-east-1.amazonaws.com/upload";

// ELEMENTS
const browseBtn =
document.getElementById("browseBtn");

const videoInput =
document.getElementById("videoInput");

const uploadBtn =
document.getElementById("uploadBtn");

const previewVideo =
document.getElementById("previewVideo");

const cameraPreview =
document.getElementById("cameraPreview");

const startRecord =
document.getElementById("startRecord");

const stopRecord =
document.getElementById("stopRecord");

let selectedFile = null;

let mediaRecorder;

let recordedChunks = [];

// =====================================
// OPEN FILE BROWSER
// =====================================
browseBtn.addEventListener("click", () => {

    videoInput.click();

});

// =====================================
// FILE SELECT
// =====================================
videoInput.addEventListener("change", (e) => {

    selectedFile = e.target.files[0];

    if(selectedFile){

        previewVideo.src =
        URL.createObjectURL(selectedFile);
    }

});

// =====================================
// START CAMERA
// =====================================
async function initCamera(){

    try{

        const stream =
        await navigator.mediaDevices.getUserMedia({

            video: true,
            audio: true

        });

        cameraPreview.srcObject = stream;

        mediaRecorder =
        new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (event)=>{

            recordedChunks.push(event.data);

        };

        mediaRecorder.onstop = ()=>{

            const blob =
            new Blob(recordedChunks, {

                type: "video/mp4"

            });

            selectedFile =
            new File(
                [blob],
                "recorded-video.mp4",
                {
                    type: "video/mp4"
                }
            );

            previewVideo.src =
            URL.createObjectURL(selectedFile);

            recordedChunks = [];
        };

    }catch(error){

        console.log(error);

        alert("Camera Access Denied");
    }
}

initCamera();

// =====================================
// START RECORDING
// =====================================
startRecord.addEventListener("click", ()=>{

    if(mediaRecorder){

        mediaRecorder.start();

        alert("Recording Started");
    }

});

// =====================================
// STOP RECORDING
// =====================================
stopRecord.addEventListener("click", ()=>{

    if(mediaRecorder){

        mediaRecorder.stop();

        alert("Recording Stopped");
    }

});

// =====================================
// UPLOAD VIDEO
// =====================================
uploadBtn.addEventListener("click", async ()=>{

    try{

        if(!selectedFile){

            alert("Select Video First");

            return;
        }

        // GET PRESIGNED URL
        const response =
        await fetch(`${API_BASE}/upload`);

        const data =
        await response.json();

        const uploadURL =
        data.uploadURL;

        const videoKey =
        data.videoKey;

        console.log(videoKey);

        // UPLOAD TO S3
        await fetch(uploadURL, {

            method: "PUT",

            headers: {
                "Content-Type": "video/mp4"
            },

            body: selectedFile
        });

        // SAVE VIDEO KEY
        localStorage.setItem(
            "videoKey",
            videoKey
        );

        alert("Upload Successful");

        // REDIRECT
        window.location.href =
        "processing.html";

    }catch(error){

        console.log(error);

        alert("Upload Failed");
    }

});