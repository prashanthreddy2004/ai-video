const API_URL =
"https://50rlwa0agc.execute-api.us-east-1.amazonaws.com/result";

const statusText =
document.getElementById("statusText");

const communicationScore =
document.getElementById("communicationScore");

const confidenceScore =
document.getElementById("confidenceScore");

const technicalScore =
document.getElementById("technicalScore");

const overallScore =
document.getElementById("overallScore");

const analysisText =
document.getElementById("analysisText");

const resumeLink =
document.getElementById("resumeLink");

const clipVideo =
document.getElementById("clipVideo");

// =====================================
// LOAD RESULTS
// =====================================
async function loadResults(){

    try{

        const videoKey =
        localStorage.getItem("videoKey");

        if(!videoKey){

            statusText.innerHTML =
            "No Video Found";

            return;
        }

        const response =
        await fetch(

            `${API_URL}?videoKey=${encodeURIComponent(videoKey)}`

        );

        const data =
        await response.json();

        console.log(data);

        // WAIT
        if(data.status === "PROCESSING"){

            statusText.innerHTML =
            "AI Processing...";

            setTimeout(loadResults,5000);

            return;
        }

        // =====================================
        // SHOW RESULTS
        // =====================================
        statusText.innerHTML =
        "Analysis Completed";

        communicationScore.innerHTML =
        data.communication_score || 0;

        confidenceScore.innerHTML =
        data.confidence_score || 0;

        technicalScore.innerHTML =
        data.technical_score || 0;

        overallScore.innerHTML =
        data.overall_score || 0;

        analysisText.innerHTML =
        data.analysis || "No Analysis";

        // RESUME
        resumeLink.href =
        data.resume_html;

        // VIDEO
        clipVideo.src =
        data.highlight_clip;

    }catch(error){

        console.log(error);

        statusText.innerHTML =
        "Failed To Load Results";
    }
}

loadResults();