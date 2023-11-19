async function showAnonymousWarning() {
    const expires = localStorage.getItem("refresh-expires");
    const lastWarning = localStorage.getItem("last-anonymous-warning");

    // only show warning every 12 hours
    if (expires && (!lastWarning || Number(lastWarning) < new Date().getTime() - 1000 * 60 * 60 * 12)) {
        document.getElementById("anonymous-warning").style.display = "block";
        document.getElementById("anonymous-warning-time").textContent = getRelativeDate(Number(expires));
        localStorage.setItem("last-anonymous-warning", new Date().getTime());
    }
}

function getRelativeDate(/** @type {number} */ timestamp) {
    const rtf = new Intl.RelativeTimeFormat('en', { numeric: "auto" })

    const deltaMs = timestamp - Date.now();

    const deltaHour = deltaMs / 1000 / 60 / 60;
    const deltaDay = deltaHour / 24;
    const deltaMonth = deltaDay / 30;

    if (deltaDay >= 29) return rtf.format(Math.round(deltaMonth), "months");
    if (deltaHour >= 23) return rtf.format(Math.round(deltaDay), "days");
    if (deltaHour >= 0.9) return rtf.format(Math.round(deltaHour), "hours");
    return "in less than an hour";
}

function showError(message) {
    alert(message);
}


class Upload {
    /**@type {FormData} @readonly*/
    formData;
    /**@type {XMLHttpRequest} @readonly*/
    xhr;
    /**@type {HTMLDivElement} @readonly*/
    videoDiv;
    /**@type {HTMLDivElement} @readonly*/
    progressText;
    /**@type {HTMLDivElement} @readonly*/
    progressBar;
    /**@type {HTMLDivElement} @readonly*/
    progressStatus;
    /**@type {boolean} @readonly*/
    valid;
    constructor(/**@type {File}*/ file) {
        if (!file.type.includes("video/")) return this.invalid("File is not a video.");
        if (file.size > 500 * 1024 * 1024) return this.invalid("File is too big. (>500MB)");
        this.valid = true;
        this.formData = new FormData(); 
        this.formData.append("file", file, file.name);
        this.videoDiv = document.getElementById("videotemplate").content.cloneNode(true).querySelector("div.videobox");
        this.progressText = this.videoDiv.querySelector("div.progress-text");
        this.progressBar = this.videoDiv.querySelector("div.progress-bar");
        this.progressStatus = this.videoDiv.querySelector("div.progress-status");
        this.videoDiv.querySelector("span.title").innerText = file.name;
        document.getElementById("uploadbar").insertAdjacentElement("afterend", this.videoDiv);
    }
    /**@private */
    invalid(/**@type {string}*/ reason) {
        this.valid = false;
        showError(reason);
    }
    send() {
        const myself = this;
        this.xhr = new XMLHttpRequest();
        this.xhr.open("POST", "/api/upload");
        this.xhr.upload.onprogress = event => { myself.progress(Math.round(event.loaded / event.total * 100)) };
        this.xhr.onload = event => { myself.uploadDone(event) };
        this.xhr.send(this.formData);
    }
    /** @private */
    progress(/**@type {Number}*/ progress) {
        this.progressBar.style.width = progress + "%";
        this.progressStatus.innerText = progress + "%";
    }
    /** @private */
    async uploadDone(/**@type {ProgressEvent<EventTarget>}*/ event) {
        console.log(event)
        this.progressText.innerText = "Converting...";
        try {
            const response = JSON.parse(this.xhr.responseText);
            if (response.error) {
                return showError(response.error.message);
            }
            this.videoDiv.querySelector("img.thumb").src = `/video_data/${response.video_id}/thumbnail-lowres.png`;
            this.videoDiv.querySelector("a.link").innerText = `${document.location.origin}/v/${response.video_id}`
            this.videoDiv.querySelector("a.link").href = `${document.location.origin}/v/${response.video_id}`
            while (true) {
                const res = await (await fetch(`/api/progress/${response.video_id}`)).json();
                if (res.error) {
                    return showError(res.error.message);
                }
                this.progress(Math.round(res.progress));

                if (res.progress == 100) {
                    this.done();
                    break;
                }
                
                await new Promise(resolve => setTimeout(resolve, 200));
            }
        }
        catch {
            return showError("Upload error");
        }
    }
    /** @private */
    done() {
        this.videoDiv.querySelector("div.progress-wrp").style.display = "none";
    }
}

/**
 * @typedef {{ id: string, title: string, duration: Number, views: Number }} Video
 * @typedef {{ base_url: string, videos: Video[] } | { error: { message: string } }} VideosResponse
 */

async function loadVideos(/**@type {boolean}*/ public) {
    /**@type {HTMLDivElement} */
    try {
        /**@type {VideosResponse}*/
        const response = await (await fetch("/api/videos" + (public ? "?public" : ""))).json();
        if ("error" in response) return showError(response.error.message);

        const videosListElem = document.getElementById(public ? "public-videos" : "user-videos")

        for (const video of response.videos) {
            const videoDiv = document.getElementById("videotemplate").content.cloneNode(true).querySelector("div.videobox");
            videoDiv.querySelector("div.progress-wrp").style.display = "none";
            videoDiv.querySelector("img.thumb").src = `/video_data/${video.id}/thumbnail-lowres.png`;
            videoDiv.querySelector("span.title").innerText = video.title;
            videoDiv.querySelector("a.link").href = `${response.base_url}/v/${video.id}`;
            videoDiv.querySelector("a.link").innerText = `${response.base_url}/v/${video.id}`;

            videosListElem.appendChild(videoDiv);
        }
    }
    catch {
        showError("unknown error");
    }
}


(async () => {
    // wait until auth has gotten a user (i know this is a dumb way but it works)
    while (!window.user) await new Promise(resolve => setTimeout(resolve, 500));
    /** @type { import("./auth.js").User } */
    const user = window.user

    if (user.type == "anonymous") {
        showAnonymousWarning();
    }
    document.getElementById("file").onchange = event => {
        const upload = new Upload(event.target.files[0]);
        if (!upload.valid) return;
        upload.send();
    }
    loadVideos(false);
    loadVideos(true);
})()