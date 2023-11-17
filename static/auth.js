// wrap the entire script in an async functio to be able to use await
(async () => {
// some typedef
/**
 * @typedef { { message: string } } AuthError
 * @typedef { "anonymous" | "normal" | "admin" } UserType
 * @typedef { { uid: number, type: UserType, username: string } } User
 * @typedef { { user: User, refresh_token?: string } | { error: AuthError } } GetSessionResponse
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
        if (result.error) {
            // auth error, delete refresh token and retry
            localStorage.removeItem("refresh-token")
            return getSession(retry + 1);
        }
        if (result.refresh_token) {
            // result includes a refresh token, so remember it
            // this only happens for anonymous sessions
            localStorage.setItem("refresh-token", result.refresh_token);
        }
        // set the user on window so it's accessible everywhere
        window.user = result.user;
    }
    catch {
        getSession(retry + 1)
    }
}
await getSession();

async function init() {
    if (document.readyState != 'complete') return;

    /** @type { User } */
    const user = window.user;
    if (!user) return;

    document.getElementById("header-username").innerText = user.username;
    document.getElementById("header-anonymous").style.display = (user.type == "anonymous") ? "inline" : "none";
}

document.onreadystatechange = init;
init();

})()