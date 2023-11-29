/**
 * @typedef { { message: string, display?: boolean } } AuthError
 * @typedef { { token: string, expires: number } } RefreshToken
 */

/** @returns {Promise<{ result?: AuthResult, error?: AuthError }>} */
async function sendForm(/**@type {string}*/url, /**@type {FormData}*/formData) {
    function toJson(/**@type {number}*/ status, /**@type {string}*/text) {
        try {
            const result = JSON.parse(text);
            if (!result.refresh && !result.error) return { "error": { "message": `Invalid server response` } }
            return result;
        }
        catch {
            return { "error": { "message": `Unknown error (${status})` } }
        }
    }
    return new Promise(resolve => {
        const req = new XMLHttpRequest();
        req.open("POST", url);
        req.onload = () => resolve(toJson(req.status, req.response));
        req.onerror = () => resolve(toJson(req.status, req.response));
        req.send(formData)
    })
}

function showError(message) {
    alert(message);
}

function showForm(doSignUp) {
    document.querySelector("div#loginform").style.display = "unset";
    document.querySelector("div#loginform>h2").innerText = doSignUp ? "Sign up" : "Log in";
    document.getElementById("loginform").style.height = `calc((1.1rem + 22px + 27px) * ${doSignUp ? "3" : "2"} + 25px + 1rem + 28px + 33px + 18px + 40px)`;
    document.getElementById("login-form").style.display = doSignUp ? "none" : ""
    document.getElementById("signup-form").style.display = doSignUp ? "" : "none"
    document.getElementById("loadingscreen").style.display = "none";

    document.getElementById("login-switchlink-signup").onclick = evt => { switchForm("signup"); evt.preventDefault(); }
    document.getElementById("login-switchlink-login").onclick = evt => { switchForm("login"); evt.preventDefault(); }
}
function switchForm(name) {
    if (name == "login") {
        window.history.pushState(null, "", "/login");
        document.title = `Login - ${sitename}`;
        showForm(false);
    }
    else {
        window.history.pushState(null, "", "/signup");
        document.title = `Sign Up - ${sitename}`;
        showForm(true);
    }
}

async function login() {
    const loginLoader = document.getElementById("login-loader")
    const loginError = document.getElementById("login-error");

    loginLoader.style.display = "block";

    const formData = new FormData(document.querySelector("form#login-form"));
    const res = await sendForm("/api/login", formData)

    loginLoader.style.display = "";

    if (res.error) {
        if (!res.error.display) return showError(res.error.message)

        loginError.innerText = res.error.message;
        loginError.style.opacity = 1;
        return;
    }
    storeToken(res.refresh);
}

async function signUp() {
    const loginLoader = document.getElementById("login-loader")
    const signUpError = document.getElementById("signup-error");

    if (document.getElementById("signup-pwd").value != document.getElementById("signup-pwd-2").value) {
        signUpError.innerText = "Passwords don't match.";
        signUpError.style.opacity = 1;
        return;
    }
    loginLoader.style.display = "block";

    const formData = new FormData(document.querySelector("form#signup-form"));

    const res = await sendForm("/api/signup", formData)

    loginLoader.style.display = "";

    if (res.error) {
        if (!res.error.display) return showError(res.error.message)

        signUpError.innerText = res.error.message;
        signUpError.style.opacity = 1;
        return;
    }
    storeToken(res.refresh);
}

function storeToken(/**@type {RefreshToken}*/refresh) {
    localStorage.setItem("refresh-token", refresh.token);
    localStorage.setItem("refresh-expires", refresh.expires);

    document.location.pathname = "/";
}

async function initLogin() {
    const doSignUp = document.location.pathname.endsWith("/signup")

    showForm(doSignUp);

    window.addEventListener("popstate", () => {
        const doSignUp = document.location.pathname.endsWith("/signup")
        showForm(doSignUp);
    });
}