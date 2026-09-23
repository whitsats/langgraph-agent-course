const API = "/api";
let state = { token: null, user: null, feedCursor: null, viewingUserId: null };

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

async function api(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (state.token) headers["Authorization"] = "Token " + state.token;
    const res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");
    return data;
}

function showPage(id) {
    $$(".page").forEach(p => p.style.display = "none");
    $(id).style.display = "block";
}

function formatTime(t) {
    const d = new Date(t + "Z");
    const now = new Date();
    const diff = Math.floor((now - d) / 1000);
    if (diff < 60) return "刚刚";
    if (diff < 3600) return Math.floor(diff / 60) + "分钟前";
    if (diff < 86400) return Math.floor(diff / 3600) + "小时前";
    return d.toLocaleDateString("zh-CN");
}

function renderPost(post, showAuthor) {
    const card = document.createElement("div");
    card.className = "post-card";
    let html = "";
    if (showAuthor && post.author) {
        html += `<span class="post-author" data-user-id="${post.author.id}">${post.author.nickname}</span> `;
    }
    html += `<div class="post-content">${post.content}</div>`;
    html += `<span class="post-time">${formatTime(post.created_at)}</span>`;
    if (state.user && post.user_id === state.user.id) {
        html += ` <button class="post-delete" data-post-id="${post.id}">删除</button>`;
    }
    card.innerHTML = html;
    card.querySelectorAll(".post-author").forEach(el => {
        el.addEventListener("click", () => viewProfile(parseInt(el.dataset.userId)));
    });
    card.querySelectorAll(".post-delete").forEach(el => {
        el.addEventListener("click", async () => {
            await api("DELETE", "/posts/" + el.dataset.postId);
            card.remove();
        });
    });
    card.addEventListener("click", (e) => {
        if (!e.target.closest(".post-author") && !e.target.closest(".post-delete")) {
            viewPostDetail(post.id);
        }
    });
    card.style.cursor = "pointer";
    return card;
}

// Auth
$("#btn-login").addEventListener("click", () => { showAuth("login"); });
$("#btn-register").addEventListener("click", () => { showAuth("register"); });
$("#btn-logout").addEventListener("click", async () => {
    try { await api("POST", "/auth/logout"); } catch (e) {}
    state.token = null; state.user = null; state.feedCursor = null;
    updateNav();
    showAuth("login");
});

function updateNav() {
    const nav = { login: $("#btn-login"), register: $("#btn-register"), logout: $("#btn-logout"), greeting: $("#nav-greeting") };
    if (state.user) {
        nav.login.style.display = "none";
        nav.register.style.display = "none";
        nav.logout.style.display = "inline";
        nav.greeting.textContent = "你好, " + state.user.nickname;
    } else {
        nav.login.style.display = "inline";
        nav.register.style.display = "inline";
        nav.logout.style.display = "none";
        nav.greeting.textContent = "";
    }
}

function showAuth(mode) {
    showPage("#page-auth");
    $("#auth-title").textContent = mode === "login" ? "登录" : "注册";
    $("#auth-nickname").style.display = mode === "register" ? "block" : "none";
    $("#auth-submit").textContent = mode === "login" ? "登录" : "注册";
    $("#auth-toggle-link").textContent = mode === "login" ? "没有账号？去注册" : "已有账号？去登录";
    $("#auth-error").textContent = "";
    $("#auth-form").onsubmit = async (e) => {
        e.preventDefault();
        const email = $("#auth-email").value;
        const password = $("#auth-password").value;
        const nickname = $("#auth-nickname").value;
        try {
            let res;
            if (mode === "login") {
                res = await api("POST", "/auth/login", { email, password });
            } else {
                res = await api("POST", "/auth/register", { nickname, email, password });
            }
            state.token = res.token;
            state.user = res.user;
            state.feedCursor = null;
            updateNav();
            await loadFeed();
            showPage("#page-feed");
        } catch (err) {
            $("#auth-error").textContent = err.message;
        }
    };
}

$("#auth-toggle-link").addEventListener("click", (e) => {
    e.preventDefault();
    const currentMode = $("#auth-submit").textContent === "登录" ? "register" : "login";
    showAuth(currentMode);
});

// Feed
async function loadFeed(append) {
    if (!state.token) return;
    try {
        let path = "/posts/feed?limit=20";
        if (append && state.feedCursor) path += "&cursor=" + encodeURIComponent(state.feedCursor);
        const res = await api("GET", path);
        const feedList = $("#feed-list");
        if (!append) feedList.innerHTML = "";
        res.posts.forEach(p => feedList.appendChild(renderPost(p, true)));
        state.feedCursor = res.next_cursor || null;
        $("#btn-load-more").style.display = res.next_cursor ? "block" : "none";
        $("#feed-empty").style.display = feedList.children.length === 0 ? "block" : "none";

        // Load suggested users
        const sugRes = await api("GET", "/users/suggested");
        const sugList = $("#suggested-list");
        sugList.innerHTML = "";
        if (sugRes.users.length > 0) {
            $("#suggested-users").style.display = "block";
            sugRes.users.forEach(u => {
                const li = document.createElement("li");
                li.innerHTML = `<a class="suggested-user-link" data-user-id="${u.id}">${u.nickname}</a>`;
                li.querySelector("a").addEventListener("click", () => viewProfile(u.id));
                sugList.appendChild(li);
            });
        } else {
            $("#suggested-users").style.display = "none";
        }
    } catch (err) {
        console.error("Feed error:", err);
    }
}

$("#btn-post").addEventListener("click", async () => {
    const input = $("#post-input");
    try {
        const res = await api("POST", "/posts", { content: input.value });
        input.value = "";
        $("#post-char-count").textContent = "0/500";
        $("#post-error").textContent = "";
        state.feedCursor = null;
        await loadFeed(false);
    } catch (err) {
        $("#post-error").textContent = err.message;
    }
});

$("#post-input").addEventListener("input", () => {
    $("#post-char-count").textContent = $("#post-input").value.length + "/500";
});

$("#btn-load-more").addEventListener("click", () => loadFeed(true));

// Profile
async function viewProfile(userId) {
    showPage("#page-profile");
    state.viewingUserId = userId;
    try {
        const res = await api("GET", "/users/" + userId);
        const u = res.user;
        $("#profile-nickname").textContent = u.nickname;
        $("#profile-bio").textContent = u.bio || "暂无简介";
        $("#profile-stats").textContent = "关注 " + res.followee_count + " | 粉丝 " + res.follower_count + " | 动态 " + res.post_count;
        const list = $("#profile-posts-list");
        list.innerHTML = "";
        (res.posts || []).forEach(p => list.appendChild(renderPost(p, false)));
        $("#profile-posts-empty").style.display = list.children.length === 0 ? "block" : "none";

        const followBtn = $("#btn-follow");
        const unfollowBtn = $("#btn-unfollow");
        if (state.user && userId !== state.user.id) {
            if (u.is_following) {
                followBtn.style.display = "none";
                unfollowBtn.style.display = "inline";
            } else {
                followBtn.style.display = "inline";
                unfollowBtn.style.display = "none";
            }
            followBtn.onclick = async () => {
                await api("POST", "/users/" + userId + "/follow");
                viewProfile(userId);
            };
            unfollowBtn.onclick = async () => {
                await api("DELETE", "/users/" + userId + "/follow");
                viewProfile(userId);
            };
        } else {
            followBtn.style.display = "none";
            unfollowBtn.style.display = "none";
        }
    } catch (err) {
        console.error(err);
    }
}

$("#btn-back-feed").addEventListener("click", () => {
    showPage("#page-feed");
});

// Post detail
async function viewPostDetail(postId) {
    showPage("#page-post-detail");
    try {
        const res = await api("GET", "/posts/" + postId);
        const container = $("#post-detail-content");
        container.innerHTML = "";
        container.appendChild(renderPost(res.post, true));
    } catch (err) {
        console.error(err);
    }
}

$("#btn-back-from-detail").addEventListener("click", () => {
    if (state.viewingUserId) {
        viewProfile(state.viewingUserId);
    } else {
        showPage("#page-feed");
    }
});

// Init
updateNav();
showAuth("login");
