// some typedef
/**
 * @typedef { { message: string } } AuthError
 * @typedef { "anonymous" | "normal" | "admin" } UserType
 * @typedef { { uid: number, type: UserType, username: string } } User
 * @typedef { { token: string, expires: number } } AnonymousRefresh
 * @typedef { { user: User, refresh?: AnonymousRefresh } | { error: AuthError } } GetSessionResponse
 */

async function getSession(retry /**@type {number}*/ = 0) {
    // only retry twice
    if (retry > 2) return;
    try {
        const headers = {}
        const refreshToken = localStorage.getItem("refresh-token");
        if (refreshToken) {
            headers["Authorization"] = refreshToken;
        }

        /** @type { GetSessionResponse } */
        const result = await (await fetch("/api/getsession", { headers })).json()
        if ('error' in result) {
            // auth error, delete refresh token and retry
            localStorage.removeItem("refresh-token")
            return getSession(retry + 1);
        }
        if (result.refresh) {
            // result includes a refresh token, so remember it
            // this only happens for anonymous sessions
            localStorage.setItem("refresh-token", result.refresh.token);
            localStorage.setItem("refresh-expires", result.refresh.expires);
        }
        // set the user on window so it's accessible everywhere
        window.user = result.user;
    }
    catch {
        getSession(retry + 1)
    }
}

async function init() {
    if (document.readyState != 'complete') return;

    /** @type { User } */
    const user = window.user;
    if (!user) return;

    document.getElementById("header-username").innerText = user.username;
    document.getElementById("header-anonymous").style.display = (user.type == "anonymous") ? "inline" : "none";
}

(async () => {
    // run everything in an async function to be able to use awaits
    await getSession();
    document.onreadystatechange = init;
    init();
})()