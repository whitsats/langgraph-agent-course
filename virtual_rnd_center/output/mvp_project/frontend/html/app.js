const API_BASE = 'http://localhost:8000';

let currentUser = null;
let currentView = 'auth';

// DOM refs
const $ = id => document.getElementById(id);
const header = $('header');
const authView = $('auth-view');
const timelineView = $('timeline-view');
const discoverView = $('discover-view');
const profileView = $('profile-view');
const feed = $('feed');
const userList = $('user-list');
const profilePosts = $('profile-posts');
const charCount = $('char-count');
const postContent = $('post-content');
const postError = $('post-error');
const noPostsMsg = $('no-posts-msg');
const noUsersMsg = $('no-users-msg');
const noProfilePosts = $('no-profile-posts');
const profileUsername = $('profile-username');
const profileBio = $('profile-bio');

let timelinePage = 1;
let discoverPage = 1;
let hasMoreTimeline = true;
let hasMoreDiscover = true;
let loadingFeed = false;
let loadingDiscover = false;

// Auth helpers
function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
}

async function api(path, options = {}) {
    const config = {
        credentials: 'include',
        ...options,
        headers: {
            ...options.headers,
        }
    };
    if (!(config.body instanceof FormData)) {
        config.headers['Content-Type'] = config.headers['Content-Type'] || 'application/json';
    }
    const res = await fetch(`${API_BASE}${path}`, config);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Request failed');
    }
    return res.json();
}

// View switching
function showView(view) {
    [authView, timelineView, discoverView, profileView].forEach(v => v.classList.add('hidden'));
    if (view === 'auth') {
        header.classList.add('hidden');
        authView.classList.remove('hidden');
        currentView = 'auth';
    } else {
        header.classList.remove('hidden');
        if (view === 'timeline') {
            timelineView.classList.remove('hidden');
            currentView = 'timeline';
        } else if (view === 'discover') {
            discoverView.classList.remove('hidden');
            currentView = 'discover';
        } else if (view === 'profile') {
            profileView.classList.remove('hidden');
            currentView = 'profile';
        }
    }
}

// Auth tabs
$('tab-login').addEventListener('click', () => {
    $('tab-login').classList.add('active');
    $('tab-register').classList.remove('active');
    $('login-form').classList.remove('hidden');
    $('register-form').classList.add('hidden');
});

$('tab-register').addEventListener('click', () => {
    $('tab-register').classList.add('active');
    $('tab-login').classList.remove('active');
    $('register-form').classList.remove('hidden');
    $('login-form').classList.add('hidden');
});

// Send verification code
$('btn-send-code').addEventListener('click', async () => {
    const email = $('reg-email').value;
    if (!email) { $('register-error').textContent = 'Enter email first'; return; }
    try {
        await api('/api/auth/send-code', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
        $('register-error').textContent = 'Code sent! Check console.';
    } catch (e) {
        $('register-error').textContent = e.message;
    }
});

// Login
$('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    $('login-error').textContent = '';
    try {
        const data = await api('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                email: $('login-email').value,
                password: $('login-password').value
            })
        });
        currentUser = data;
        showView('timeline');
        loadTimeline();
    } catch (e) {
        $('login-error').textContent = e.message;
    }
});

// Register
$('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    $('register-error').textContent = '';
    try {
        const data = await api('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                username: $('reg-username').value,
                email: $('reg-email').value,
                password: $('reg-password').value,
                code: $('reg-code').value
            })
        });
        currentUser = data;
        showView('timeline');
        loadTimeline();
    } catch (e) {
        $('register-error').textContent = e.message;
    }
});

// Logout
$('btn-logout').addEventListener('click', async () => {
    await api('/api/auth/logout', { method: 'POST' });
    currentUser = null;
    showView('auth');
});

// Navigation
$('btn-nav-home').addEventListener('click', () => {
    showView('timeline');
    loadTimeline();
});

$('btn-nav-discover').addEventListener('click', () => {
    showView('discover');
    loadDiscover();
});

$('btn-nav-profile').addEventListener('click', () => {
    if (currentUser) {
        showView('profile');
        loadProfile(currentUser.id);
    }
});

// Character count
postContent.addEventListener('input', () => {
    charCount.textContent = `${postContent.value.length}/280`;
});

// Create post
$('btn-post').addEventListener('click', async () => {
    const content = postContent.value.trim();
    if (!content) { postError.textContent = 'Content is required'; return; }
    postError.textContent = '';
    const fileInput = $('post-image');
    const formData = new FormData();
    formData.append('content', content);
    if (fileInput.files[0]) {
        formData.append('image', fileInput.files[0]);
    }
    try {
        await api('/api/posts', {
            method: 'POST',
            body: formData,
            headers: {} // Let browser set content-type for formdata
        });
        postContent.value = '';
        fileInput.value = '';
        charCount.textContent = '0/280';
        loadTimeline();
    } catch (e) {
        postError.textContent = e.message;
    }
});

// Timeline
async function loadTimeline(reset = true) {
    if (reset) {
        timelinePage = 1;
        hasMoreTimeline = true;
        feed.innerHTML = '';
    }
    if (!hasMoreTimeline || loadingFeed) return;
    loadingFeed = true;
    $('feed-loader').classList.remove('hidden');
    try {
        const data = await api(`/api/timeline?page=${timelinePage}`);
        hasMoreTimeline = data.has_more;
        if (data.posts.length === 0 && timelinePage === 1) {
            noPostsMsg.classList.remove('hidden');
        } else {
            noPostsMsg.classList.add('hidden');
            data.posts.forEach(p => feed.appendChild(createPostCard(p)));
        }
        timelinePage++;
    } catch (e) {
        console.error(e);
    } finally {
        loadingFeed = false;
        $('feed-loader').classList.add('hidden');
    }
}

// Discover
async function loadDiscover(reset = true) {
    if (reset) {
        discoverPage = 1;
        hasMoreDiscover = true;
        userList.innerHTML = '';
    }
    if (!hasMoreDiscover || loadingDiscover) return;
    loadingDiscover = true;
    try {
        const data = await api(`/api/users/discover?page=${discoverPage}`);
        if (data.length === 0 && discoverPage === 1) {
            noUsersMsg.classList.remove('hidden');
        } else {
            noUsersMsg.classList.add('hidden');
            data.forEach(u => {
                const card = document.createElement('div');
                card.className = 'user-card';
                card.innerHTML = `
                    <div class="user-info">
                        <span class="username">@${u.username}</span>
                        <span class="bio">${u.bio || 'No bio'}</span>
                    </div>
                    <button class="follow-btn" data-id="${u.id}">Follow</button>
                `;
                card.querySelector('.follow-btn').addEventListener('click', async () => {
                    try {
                        await api(`/api/users/${u.id}/follow`, { method: 'POST' });
                        card.querySelector('.follow-btn').textContent = 'Following';
                        card.querySelector('.follow-btn').disabled = true;
                    } catch (e) { console.error(e); }
                });
                userList.appendChild(card);
            });
            hasMoreDiscover = data.length === 20;
            discoverPage++;
        }
    } catch (e) {
        console.error(e);
    } finally {
        loadingDiscover = false;
    }
}

// Profile
async function loadProfile(userId) {
    try {
        const user = await api(`/api/users/${userId}`);
        profileUsername.textContent = `@${user.username}`;
        profileBio.textContent = user.bio || 'No bio';

        const posts = await api(`/api/users/${userId}/posts?page=1`);
        profilePosts.innerHTML = '';
        if (posts.length === 0) {
            noProfilePosts.classList.remove('hidden');
        } else {
            noProfilePosts.classList.add('hidden');
            posts.forEach(p => profilePosts.appendChild(createPostCard(p)));
        }
    } catch (e) { console.error(e); }
}

// Create post card element
function createPostCard(post) {
    const card = document.createElement('div');
    card.className = 'post-card';
    const time = new Date(post.created_at).toLocaleString();
    let html = `
        <div class="post-header">
            <a href="#" class="post-author-link" data-id="${post.author_id}">@${post.author_id}</a>
        </div>
        <div class="post-content">${escapeHtml(post.content)}</div>
    `;
    if (post.image_path) {
        html += `<img src="${API_BASE}${post.image_path}" alt="post image" class="post-image" loading="lazy">`;
    }
    html += `<div class="post-time">${time}</div>`;
    card.innerHTML = html;

    card.querySelector('.post-author-link')?.addEventListener('click', (e) => {
        e.preventDefault();
        showView('profile');
        loadProfile(post.author_id);
    });

    return card;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Infinite scroll
window.addEventListener('scroll', () => {
    if (currentView === 'timeline') {
        const nearBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 400;
        if (nearBottom) loadTimeline(false);
    } else if (currentView === 'discover') {
        const nearBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 400;
        if (nearBottom) loadDiscover(false);
    }
});

// Auto-login check on page load
(async () => {
    const token = getCookie('session_token');
    if (token) {
        try {
            const data = await api('/api/auth/me');
            currentUser = data;
            showView('timeline');
            loadTimeline();
        } catch (e) {
            showView('auth');
        }
    }
})();
