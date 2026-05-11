const API_BASE =
"https://50rlwa0agc.execute-api.us-east-1.amazonaws.com";

const resultContainer =
document.getElementById("resultContainer");

// --------------------------------
// GET VIDEO KEY
// --------------------------------
const videoKey =
localStorage.getItem("videoKey");

if(!videoKey){

    resultContainer.innerHTML =
    "<h2>No video key found</h2>";

}else{

    loadResults();
}

// --------------------------------
// LOAD RESULTS
// --------------------------------
async function loadResults(){

    try{

        resultContainer.innerHTML =
        "<h2>Processing Interview...</h2>";

        const response =
        await fetch(
            `${API_BASE}/result?videoKey=${encodeURIComponent(videoKey)}`
        );

        const data =
        await response.json();

        console.log(data);

        // --------------------------
        // STILL PROCESSING
        // --------------------------
        if(data.status !== "completed"){

            resultContainer.innerHTML =
            "<h2>Still Processing...</h2>";

            setTimeout(loadResults,5000);

            return;
        }

        // --------------------------
        // SHOW RESULTS
        // --------------------------
        resultContainer.innerHTML = `

            <h1>Interview Analysis</h1>

            <h2>Scores</h2>

            <p>
            Communication:
            ${data.communication}/10
            </p>

            <p>
            Confidence:
            ${data.confidence}/10
            </p>

            <p>
            Technical:
            ${data.technical}/10
            </p>

            <p>
            Overall:
            ${data.overall}/10
            </p>

            <h2>AI Analysis</h2>

            <p>
            ${data.analysis}
            </p>

            <h2>Resume</h2>

            <a href="${data.resume_url}"
               target="_blank">

               Open Resume

            </a>

            <h2>Highlight Clip</h2>

            <video width="600"
                   controls>

                <source
                    src="${data.clip_url}"
                    type="video/mp4">

            </video>
        `;

    }catch(error){

        console.log(error);

        resultContainer.innerHTML =
        "<h2>Error Loading Results</h2>";
    }
}