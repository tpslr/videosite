/** @type { User } */
const user = window.user

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



if (user.type == "anonymous") {
    showAnonymousWarning();
}