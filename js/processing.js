const progress =
document.getElementById("progress");

const statusText =
document.getElementById("statusText");

let value = 0;

const interval = setInterval(()=>{

    value += 10;

    progress.style.width =
    value + "%";

    if(value >= 100){

        clearInterval(interval);

        statusText.innerHTML =
        "Completed";

        setTimeout(()=>{

            window.location.href =
            "dashboard.html";

        },2000);
    }

},1000);