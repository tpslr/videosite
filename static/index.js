async function showAnonymousWarning() {
    const expires = localStorage.getItem("refresh-expires");
    const lastWarning = localStorage.getItem("last-anonymous-warning");

    // only show warning every 12 hours
    if (expires && (!lastWarning || Number(lastWarning) < new Date().getTime() - 1000 * 60 * 60 * 12)) {
        document.getElementById("anonymous-warning").style.display = "";
        document.getElementById("anonymous-warning-time").textContent = getRelativeDate(Number(expires));
        localStorage.setItem("last-anonymous-warning", new Date().getTime());
        window.onresize = () => {
            // resize anonymous warning close button
            const warningHeight = window.getComputedStyle(document.querySelector("div#anonymous-warning")).height;
            document.querySelector("div#anonymous-warning").style.gridTemplateColumns = `auto ${warningHeight}`;
        }
        window.onresize();
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
function secondsToVideoLenght(/**@type {Number}*/ seconds) {
    return `${Math.floor(seconds / 60)}:${("0" + Math.round(seconds % 60)).slice(-2)}` 
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
    /**@type {HTMLVideoElement} @readonly*/
    thumbnailVideo;
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

        this.videoDiv.querySelector("img.thumb").style.display = "none";
        const thumbnailVideo = document.createElement("video");
        this.thumbnailVideo = thumbnailVideo;
        thumbnailVideo.className = "thumb";
        thumbnailVideo.src = URL.createObjectURL(file);
        thumbnailVideo.autoplay = false;
        thumbnailVideo.controls = false;
        thumbnailVideo.onloadedmetadata = () => {
            this.videoDiv.querySelector("div.duration").innerText = secondsToVideoLenght(this.thumbnailVideo.duration);
        }
        const thumbwrap = this.videoDiv.querySelector("div.thumbwrap");
        thumbwrap.insertBefore(thumbnailVideo, thumbwrap.firstChild);
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
            window.URL.revokeObjectURL(this.thumbnailVideo.src);
            this.thumbnailVideo.style.display = "none";
            this.videoDiv.querySelector("img.thumb").style.display = "";
            this.videoDiv.querySelector("img.thumb").src = `/video_data/${response.video_id}/thumbnail-lowres.png`;
            //this.videoDiv.querySelector("a.link").innerText = `${document.location.origin}/v/${response.video_id}`
            //this.videoDiv.querySelector("a.link").href = `${document.location.origin}/v/${response.video_id}`
            this.videoDiv.querySelector("div.duration").innerText = secondsToVideoLenght(response.duration);
            this.videoDiv.querySelector("button.copybutton").onclick = event => copyLink(event, `${document.location.origin}/v/${response.video_id}`)
            this.videoDiv.querySelector("button.delete").style.display = "";
            this.videoDiv.querySelector("button.delete").onclick = event => deleteVideo(event, response.video_id)
            
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

            this.videoDiv.querySelector("button.private").style.display = "";
            this.videoDiv.querySelector("button.private").onclick = event => privateVideo(this.videoDiv, response.video_id)
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

async function copyLink(/**@type {PointerEvent}*/ event, /**@type {string}*/link) { 
    try {
        await navigator.clipboard.writeText(link)
        event.target.classList.add("greenbutton");
        event.target.innerText = "Copied!";
        setTimeout(() => {
            event.target.classList.remove("greenbutton");
            event.target.innerText = "Copy Link";
        }, 1000);
    }
    catch {
        showError("Failed to copy, most likely browser disallows clipboard.");
    }
}

/** @returns {Promise<{ error?: AuthError }>} */
async function sendForm(/**@type {string}*/url, /**@type {FormData}*/formData, /**@type {string}*/method = "POST") {
    return new Promise(resolve => {
        const req = new XMLHttpRequest();
        req.open(method, url);
        req.onload = () => {
            if (req.response != "OK")
                return resolve(parseError(req.status, req.response));
            resolve({})
        }
        req.onerror = () => resolve(parseError(req.status, req.response));
        req.send(formData)
    })
}

/** @returns { AuthError } */
function parseError(/**@type {number}*/ status, /**@type {string}*/text) {
    try {
        const result = JSON.parse(text);
        if (result.error) return result.error;
        return { "message": `Invalid server response` }
    }
    catch {
        return { "message": `Unknown error (${status})` }
    }
}

async function deleteVideo(/**@type {PointerEvent}*/ event, /**@type {string}*/videoId) {
    const response = await fetch(`/api/video/${videoId}`, { method: "DELETE" });
    if (response.ok) {
        /**@type { HTMLDivElement } */
        const videoBox = event.target.closest("div.videobox");
        videoBox.parentElement.removeChild(videoBox);
        return;
    }
    const error = parseError(await response.text());
    showError(error.message);
}

async function privateVideo(/**@type {HTMLDivElement}*/ videoDiv, /**@type {string}*/videoId) {
    const private = !videoDiv.classList.contains("private");

    const formData = new FormData()
    formData.append("action", private ? "set_private" : "set_public");
    const result = await sendForm(`/api/video/${videoId}`, formData, "PATCH");

    if (result.error) {
        return showError(result.error.message);
    }

    videoDiv.classList.toggle("private");

    videoDiv.querySelector("button.private").innerText = private ? "Make Public" : "Make Private";
}

/**
 * @typedef {{ id: string, title: string, owner: string, duration: Number, views: Number, private?: boolean }} Video
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
            videoDiv.querySelector("div.duration").innerText = secondsToVideoLenght(video.duration);
            if (public) {
                videoDiv.querySelector("a.link").style.display = "none";
                videoDiv.querySelector("span.owner").style.display = "unset";
                videoDiv.querySelector("span.owner").innerText = video.owner;
            }
            else {
                //videoDiv.querySelector("a.link").href = `${response.base_url}/v/${video.id}`;
                //videoDiv.querySelector("a.link").innerText = `${response.base_url}/v/${video.id}`;

                videoDiv.querySelector("button.delete").style.display = "";
                videoDiv.querySelector("button.delete").onclick = event => deleteVideo(event, video.id)

                videoDiv.querySelector("button.private").style.display = "";
                videoDiv.querySelector("button.private").onclick = event => privateVideo(videoDiv, video.id)
                videoDiv.querySelector("button.private").innerText = video.private ? "Make Public" : "Make Private";

                if (video.private) videoDiv.classList.add("private");
            }
            videoDiv.querySelector("div.video").onclick = () => { document.location = `${response.base_url}/v/${video.id}`; }
            videoDiv.querySelector("button.copybutton").onclick = event => copyLink(event, `${response.base_url}/v/${video.id}`)
            videosListElem.appendChild(videoDiv);
        }
    }
    catch {
        showError("unknown error");
    }
}

function allowDrag(e) {
    e.dataTransfer.dropEffect = 'copy';
    e.preventDefault();
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
    await loadVideos(false);
    await loadVideos(true);

    document.querySelector("div#loading-wrap").style.display = "none";

    const dropfile = document.getElementById('dropfile');

    window.addEventListener('dragenter', function(e) {
        dropfile.style.display = "block";
    });
    dropfile.addEventListener('dragenter', allowDrag);
    dropfile.addEventListener('dragover', allowDrag);
    dropfile.addEventListener('dragleave', function(e) {
        console.log('dragleave');
        dropfile.style.display = "none";
    });
    dropfile.addEventListener('drop', (e) => {
        e.preventDefault();
        dropfile.style.display = "none";
        const upload = new Upload(e.dataTransfer.files[0]);
        if (!upload.valid) return;
        upload.send();
    });
})()