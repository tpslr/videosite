const href = document.location.href.split("/");

// video id will be last part of url
const videoId = href[href.length - 1];

async function onLoad() {
    window.onresize = () => { document.querySelector("div#comments").style.width = window.getComputedStyle(document.querySelector("video")).width.replace("px", "") - 20 + "px"; }
    window.onresize();
    loadComments();

    const video = document.querySelector("video");
    let lastT = 0;
    while (true) {
        let t = video.duration < 15 ? 15 - video.duration : 0;
        for (let i = 0; i < video.played.length; i++) {
            t += video.played.end(i) - video.played.start(i);
        }
        if (t != lastT) await fetch(document.location.href + "/view", { headers: { "T": t } });
        lastT = t;
        await new Promise(resolve => setTimeout(resolve, 4000));
    }
}
async function loadComments() {
    // wait until auth has gotten a user (i know this is a dumb way but it works)
    while (!window.user) await new Promise(resolve => setTimeout(resolve, 500));

    /**@type { { owner: string, content: string }[] } */
    const comments = await (await fetch(`/api/video/${videoId}/comments`)).json()

    document.querySelector("#comments-title").innerText = `${comments.length} Comments`;

    const commentTemplate = document.querySelector("template#comment")
    const commentsElem = document.querySelector("div#comments")

    for (const comment of comments) {
        const commentDiv = commentTemplate.content.cloneNode(true).querySelector("div.comment");

        commentDiv.querySelector(".user").innerText = comment.username;
        commentDiv.querySelector(".content").innerText = comment.content;

        commentsElem.appendChild(commentDiv)
    }
}

async function postComment() {
    const commentContent = document.querySelector("input#comment").value;

    const formData = new FormData();
    formData.append("content", commentContent);
    const result = await sendForm(`/api/video/${videoId}/comment`, formData);
    if (result.error) {
        return alert(result.error.message);
    }

    const commentDiv = document.querySelector("template#comment").content.cloneNode(true).querySelector("div.comment");

    commentDiv.querySelector(".user").innerText = window.user.username;
    commentDiv.querySelector(".content").innerText = commentContent;

    document.querySelector("div.commentbox").insertAdjacentElement("afterend", commentDiv);
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