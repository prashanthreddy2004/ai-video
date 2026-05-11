const API_URL =
"https://50rlwa0agc.execute-api.us-east-1.amazonaws.com/upload";

const cameraPreview =
document.getElementById("cameraPreview");

const previewVideo =
document.getElementById("previewVideo");

const browseBtn =
document.getElementById("browseBtn");

const videoInput =
document.getElementById("videoInput");

const uploadBtn =
document.getElementById("uploadBtn");

const startRecord =
document.getElementById("startRecord");

const stopRecord =
document.getElementById("stopRecord");

let mediaRecorder;
let recordedChunks = [];
let selectedFile = null;

// -----------------------------
// OPEN CAMERA
// -----------------------------
async function startCamera(){

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

            if(event.data.size > 0){

                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = ()=>{

            const blob =
            new Blob(recordedChunks,{
                type:"video/webm"
            });

            selectedFile =
            new File(
                [blob],
                "recorded-video.webm",
                {type:"video/webm"}
            );

            const videoURL =
            URL.createObjectURL(blob);

            previewVideo.src =
            videoURL;
        };

    }catch(error){

        console.log(error);

        alert("Camera access denied");
    }
}

startCamera();

// -----------------------------
// START RECORDING
// -----------------------------
startRecord.addEventListener("click",()=>{

    recordedChunks = [];

    mediaRecorder.start();

    alert("Recording Started");
});

// -----------------------------
// STOP RECORDING
// -----------------------------
stopRecord.addEventListener("click",()=>{

    mediaRecorder.stop();

    alert("Recording Stopped");
});

// -----------------------------
// BROWSE VIDEO
// -----------------------------
browseBtn.addEventListener("click",()=>{

    videoInput.click();
});

// -----------------------------
// SELECT VIDEO
// -----------------------------
videoInput.addEventListener("change",(event)=>{

    selectedFile =
    event.target.files[0];

    if(selectedFile){

        previewVideo.src =
        URL.createObjectURL(selectedFile);
    }
});

// -----------------------------
// UPLOAD VIDEO
// -----------------------------
uploadBtn.addEventListener("click",async()=>{

    try{

        if(!selectedFile){

            alert("Please record or select video");

            return;
        }

        const formData =
        new FormData();

        formData.append(
            "video",
            selectedFile
        );

        const response =
        await fetch(API_URL,{
            method:"POST",
            body:formData
        });

        const data =
        await response.json();

        console.log(data);

        if(data.videoKey){

            localStorage.setItem(
                "videoKey",
                data.videoKey
            );

            window.location.href =
            "processing.html";

        }else{

            alert("Upload Failed");
        }

    }catch(error){

        console.log(error);

        alert("Upload Error");
    }
});