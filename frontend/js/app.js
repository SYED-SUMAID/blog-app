(() => {
  "use strict";

  // The Docker Compose setup exposes FastAPI on port 8000. Override this
  // value with window.JOURNAL_API_BASE before this script if your API is elsewhere.
  const API_PROTOCOL = location.protocol === "file:" ? "http:" : location.protocol;
  const API_BASE = (window.JOURNAL_API_BASE || document.querySelector('meta[name="journal-api-base"]')?.content || `${API_PROTOCOL}//${location.hostname || "127.0.0.1"}:8000`).replace(/\/$/, "");
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k) { try { return window.localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { window.localStorage.setItem(k, v); } catch {} },
    del(k) { try { window.localStorage.removeItem(k); } catch {} }
  };

  let token = store.get("access_token") || "";
  let currentUser = null;
  let blogs = [];
  let currentBlog = null;
  let authMode = "login";
  let activeFilter = "All";
  let searchTerm = "";
  let likedBlogs = new Set();
  let followedUsers = new Set();
  let toastTimer = null;

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
      "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
    })[c]);
  }
  // Keeps Arabic phrases inside English text intact: brackets stay in place and the phrase never splits across lines.
  const ARABIC = "\\u0600-\\u06FF\\u0750-\\u077F\\u08A0-\\u08FF\\uFB50-\\uFDFF\\uFE70-\\uFEFF";
  const ARABIC_RUN = new RegExp(`[${ARABIC}]+(?:[ \\u00A0\\u200C\\u200D]+[${ARABIC}]+)*`, "g");
  function bidi(html) { return html.replace(ARABIC_RUN, run => `<span class="ar" lang="ar" dir="rtl">${run}</span>`); }
  // Story categories. A story's category comes from blog.category when the API sends one,
  // then from a [[category:Name]] line written by the editor, then from its words.
  // Filter chips and card labels are built from this list. When the backend is connected, send a `category` field on each blog and keep these names in sync.
  const CATEGORIES = ["Technology", "History", "Religion", "Fashion", "Markets", "Lifestyle", "General"];
  const CATEGORY_MARKER = /^\s*\[\[category:\s*([A-Za-z]+)\s*\]\]\s*/;
  const CATEGORY_HINTS = {
    Technology: /\b(?:tech\w*|software|ai|artificial|app|apps|digital|internet|computer\w*|cod(?:e|ing)|data|robot\w*|gadget\w*|smartphone\w*|cyber\w*|startup\w*|algorithm\w*|online)\b/gi,
    History: /\b(?:histor\w+|ancient|empire\w*|dynast\w+|civili[sz]ation\w*|century|centuries|medieval|war|wars|revolution\w*|heritage|era)\b/gi,
    Religion: /\b(?:relig\w+|islam\w*|imam\w*|qur'?an\w*|hadith|faith\w*|pray\w*|allah|god|church|mosque|sunnah|spiritual\w*)\b|[\u0600-\u06FF]+/gi,
    Fashion: /\b(?:fashion\w*|outfit\w*|wardrobe\w*|cloth\w+|designer\w*|runway|couture|apparel|trend\w*|textile\w*)\b/gi,
    Markets: /\b(?:market\w*|stock\w*|invest\w*|econom\w+|financ\w+|trad(?:e|es|ing|er|ers)|crypto\w*|business\w*|inflation|bank\w*|profit\w*)\b/gi,
    Lifestyle: /\b(?:life|habit\w*|mindful\w*|slow\w*|courage|growth|wellbeing|health\w*|routine\w*|calm|self|balance|motivation\w*)\b/gi
  };
  const storyText = (blog) => String(blog.content || "").replace(CATEGORY_MARKER, "");
  // Display only: removes markdown marks such as "# " and *emphasis* that were typed into a story.
  const plain = (text) => String(text || "").replace(/^[ \t]{0,3}#{1,6}[ \t]+/gm, "").replace(/(\*{1,2})([^*\n]+)\1/g, "$2").replace(/`([^`\n]+)`/g, "$1");
  function withoutTitle(text, title) {
    const t = title.trim(), s = text.trim();
    return t && s.toLowerCase().startsWith(t.toLowerCase()) ? s.slice(t.length).replace(/^[\s:\u2013\u2014-]+/, "") : s;
  }
  function categoryOf(blog) {
    const pick = (value) => CATEGORIES.find(name => name.toLowerCase() === String(value || "").trim().toLowerCase());
    const tagged = pick(blog.category) || pick((String(blog.content || "").match(CATEGORY_MARKER) || [])[1]);
    if (tagged) return tagged;
    const title = plain(blog.title), text = storyText(blog).slice(0, 800);
    let best = "General", top = 0;
    for (const [name, pattern] of Object.entries(CATEGORY_HINTS)) {
      const score = 3 * (title.match(pattern) || []).length + (text.match(pattern) || []).length;
      if (score > top) { best = name; top = score; }
    }
    return best;
  }
  function blogId(blog) { return blog.blog_id ?? blog.id; }
  function userId(user) { return user?.id ?? user?.user_id; }
  // Author name: use whichever field the API sends; for your own stories fall back to the signed-in username.
  function authorName(blog) {
    const direct = blog.author_name || blog.author_username || blog.username || blog.author?.username || blog.author?.name || blog.user?.username || blog.owner?.username || (typeof blog.author === "string" ? blog.author : "");
    if (direct) return String(direct);
    if (currentUser && blog.author_id != null && String(blog.author_id) === String(userId(currentUser))) return String(currentUser.username || currentUser.name || "");
    return "";
  }
  function showToast(message) {
    const el = $("appToast");
    el.textContent = message;
    el.style.display = "block";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.style.display = "none"; }, 3600);
  }
  function setBusy(button, busy, label) {
    if (!button) return;
    if (busy) {
      button.dataset.oldText = button.textContent;
      button.disabled = true;
      button.textContent = label || "Please wait…";
      button.style.opacity = ".7";
    } else {
      button.disabled = false;
      button.textContent = button.dataset.oldText || button.textContent;
      button.style.opacity = "";
      delete button.dataset.oldText;
    }
  }
  async function api(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.body && !(options.body instanceof FormData) && !(options.body instanceof URLSearchParams)) {
      headers["Content-Type"] = "application/json";
    }
    let response;
    try {
      response = await fetch(API_BASE + path, { ...options, headers });
    } catch (err) {
      throw new Error(`Cannot reach the Journal API at ${API_BASE}. Start the backend and check that port 8000 is reachable.`);
    }
    if (response.status === 401 && token && path !== "/token") {
      clearSession();
      updateNav();
      throw new Error("Your session expired. Please sign in again.");
    }
    if (!response.ok) {
      let message = `Request failed (${response.status})`;
      try {
        const data = await response.json();
        if (typeof data.detail === "string") message = data.detail;
        else if (Array.isArray(data.detail)) message = data.detail.map(x => x.msg).join(", ");
        else if (data.message) message = data.message;
      } catch {}
      const error = new Error(message);
      error.status = response.status;
      throw error;
    }
    if (response.status === 204) return null;
    const type = response.headers.get("content-type") || "";
    return type.includes("application/json") ? response.json() : null;
  }

  function clearSession() {
    token = "";
    currentUser = null;
    store.del("access_token");
    likedBlogs.clear();
    followedUsers.clear();
  }
  function stateKey(prefix) {
    return `${prefix}_${currentUser?.id ?? currentUser?.username ?? "guest"}`;
  }
  function loadLocalActionState() {
    try {
      likedBlogs = new Set(JSON.parse(store.get(stateKey("journal_likes")) || "[]").map(String));
      followedUsers = new Set(JSON.parse(store.get(stateKey("journal_follows")) || "[]").map(String));
    } catch { likedBlogs = new Set(); followedUsers = new Set(); }
  }
  function saveLocalActionState() {
    if (!currentUser) return;
    store.set(stateKey("journal_likes"), JSON.stringify([...likedBlogs]));
    store.set(stateKey("journal_follows"), JSON.stringify([...followedUsers]));
  }

  function updateNav() {
    const authButton = $("authNavButton");
    const signOut = $("signOutButton");
    if (token && currentUser) {
      const name = String(currentUser.username || "Account");
      authButton.className = "account-btn";
      authButton.innerHTML = `<span class="av" aria-hidden="true">${esc(name.charAt(0).toUpperCase())}</span><span class="name">${esc(name)}</span>`;
      authButton.setAttribute("aria-label", `Signed in as ${name}`);
      authButton.title = `Signed in as ${name}`;
      authButton.disabled = true;
      signOut.classList.remove("hidden");
    } else {
      authButton.className = "app-btn secondary sm";
      authButton.textContent = "Sign in";
      authButton.removeAttribute("aria-label");
      authButton.title = "Sign in to Journal";
      authButton.disabled = false;
      signOut.classList.add("hidden");
    }
  }
  function setWriting(on) { document.body.classList.toggle("writing", on); }
  async function loadMe() {
    if (!token) { currentUser = null; updateNav(); return; }
    try {
      currentUser = await api("/user/me");
      loadLocalActionState();
    } catch {
      clearSession();
    }
    updateNav();
  }

  function showStories({ query = "", focus = false, navigate = true } = {}) {
    const fromArticle = !$("articlePage").classList.contains("hidden");
    if (!document.body.classList.contains("stories-page")) {
      document.body.classList.add("stories-page");
      if (navigate) history.pushState({ journalPage: "stories" }, "", "#stories");
    }
    $("latest-stories").hidden = false;
    $("articlePage").classList.add("hidden");
    $("editorPanel").classList.add("hidden");
    setWriting(false);
    searchTerm = query.trim();
    $("blogQuery").value = query;
    renderBlogs();
    window.scrollTo({ top: fromArticle ? listScroll : 0, behavior: "auto" });
    if (focus) setTimeout(() => $("blogQuery").focus(), 150);
  }
  function showHome({ navigate = true } = {}) {
    document.body.classList.remove("stories-page");
    $("articlePage").classList.add("hidden");
    $("editorPanel").classList.add("hidden");
    $("latest-stories").hidden = true;
    setWriting(false);
    if (navigate && location.hash === "#stories") {
      history.pushState({ journalPage: "home" }, "", location.pathname + location.search);
    }
    window.scrollTo({ top: 0, behavior: "auto" });
  }
  async function refreshBlogs() {
    const grid = $("grid");
    grid.innerHTML = SKELETON.repeat(4);
    $("count").textContent = "";
    setFeedEnd("");
    feedDone = false; feedLoading = false; feedError = false; nextCursor = null; shownCount = 0;
    const ticket = ++feedTicket; // ignore an answer that belongs to an older refresh
    try {
      const first = await fetchBatch(null);
      if (ticket !== feedTicket) return;
      blogs = first;
      nextCursor = first.length ? Number(blogId(first[first.length - 1])) : null;
      feedDone = first.length < BATCH;
      renderBlogs();
    } catch (error) {
      blogs = [];
      feedDone = true;
      $("count").textContent = "";
      grid.innerHTML = `<div class="connection-note"><b>Stories could not be loaded.</b><br>${esc(error.message)}<br><button class="ghost-btn" id="retryStories" type="button">Try again</button></div>`;
      $("retryStories").addEventListener("click", refreshBlogs);
    }
  }
  const BATCH = 8; // stories per request (cursor paging)
  let nextCursor = null, feedDone = false, feedLoading = false, feedError = false;
  let shownCount = 0, feedKey = "", feedTicket = 0, listScroll = 0;
  const SKELETON = '<div class="skel" aria-hidden="true"><i></i><i></i><i></i><i class="s"></i></div>';
  function renderBlogs({ append = false } = {}) {
    const grid = $("grid");
    // The filter bar always lists every category so it stays stable once the backend supplies them.
    const present = CATEGORIES;
    const filtered = blogs; // search and topic filters are applied by the API (see fetchBatch)
    $("chips").innerHTML = ["All", ...present].map(category =>
      `<button class="chip" type="button" data-filter="${category}" aria-pressed="${activeFilter === category}">${category}</button>`
    ).join("");
    $("count").textContent = feedDone && filtered.length ? `${filtered.length} ${filtered.length === 1 ? "story" : "stories"}` : "";
    const key = `${activeFilter}|${searchTerm}`;
    const keyChanged = key !== feedKey;
    if (keyChanged) feedKey = key;
    if (!filtered.length) {
      grid.innerHTML = (searchTerm || activeFilter !== "All")
        ? `<p class="none">${searchTerm ? `No stories match \u201c${esc(searchTerm)}\u201d${activeFilter === "All" ? "" : ` in ${esc(activeFilter)}`}. Try another word.` : `No ${esc(activeFilter)} stories yet.`}</p>`
        : `<p class="none">No stories have been published yet. Be the first to share one.</p>`;
      shownCount = 0;
      syncFeedEnd();
      maybeLoadMore();
      return;
    }
    const card = (blog, i) => {
      const id = Number(blogId(blog));
      const rawTitle = plain(blog.title).trim();
      const title = bidi(esc(rawTitle || "Untitled story"));
      const body = withoutTitle(plain(storyText(blog)), rawTitle).replace(/\s+/g, " ");
      const excerpt = bidi(esc(body.length > 220 ? body.slice(0, 220).replace(/\s+\S*$/, "") + "…" : body));
      const authorRaw = authorName(blog);
      const author = esc(authorRaw || "Journal member");
      const initial = esc((authorRaw || "J").charAt(0).toUpperCase());
      const minutes = Math.max(1, Math.ceil(storyText(blog).trim().split(/\s+/).filter(Boolean).length / 220));
      const d = new Date(blog.created_at || blog.published_at || blog.date || "");
      const when = isNaN(d) ? "" : d.toLocaleDateString("en", { month: "short", day: "numeric", year: "numeric" });
      const cat = esc(categoryOf(blog));
      // Cover image: the backend can send image_url / cover_image / image / thumbnail.
      const src = blog.image_url || blog.cover_image || blog.image || blog.thumbnail || "";
      const media = src ? `<div class="media"><img src="${esc(src)}" alt="" loading="lazy" decoding="async"></div>` : "";
      return `<article class="card">
        <div class="body">
          <div class="card-author"><span class="av" aria-hidden="true">${initial}</span><b>${author}</b>${when ? `<small>${when}</small>` : ""}</div>
          <h3><button class="lnk" type="button" data-open-blog="${id}">${title}</button></h3>
          <p>${excerpt}</p>
          <div class="card-foot"><span class="tagc">${cat}</span><span>${minutes} min read</span></div>
        </div>${media}
      </article>`;
    };
    if (append && !keyChanged && shownCount > 0 && shownCount <= filtered.length) {
      grid.insertAdjacentHTML("beforeend", filtered.slice(shownCount).map(card).join(""));
    } else {
      grid.innerHTML = filtered.map(card).join("");
    }
    shownCount = filtered.length;
    syncFeedEnd();
    maybeLoadMore();
  }
  // ---- Endless feed: cursor paging (each request asks for stories older than the last one we have) ----
  async function fetchBatch(cursor) {
    const q = new URLSearchParams({ limit: String(BATCH) });
    if (cursor) q.set("cursor", String(cursor));
    if (searchTerm) q.set("q", searchTerm);
    if (activeFilter !== "All") q.set("category", activeFilter);
    const data = await api("/blogs?" + q.toString());
    return Array.isArray(data) ? data : [];
  }
  function setFeedEnd(state) {
    const el = $("feedEnd");
    if (state === "loading") el.innerHTML = SKELETON + SKELETON;
    else if (state === "done") el.innerHTML = '<p class="feed-note">You\u2019re all caught up.</p>';
    else if (state === "error") el.innerHTML = '<p class="feed-note">Couldn\u2019t load more stories. <button class="ghost-btn" id="feedRetry" type="button">Try again</button></p>';
    else el.innerHTML = "";
  }
  function syncFeedEnd() { setFeedEnd(feedError ? "error" : feedLoading ? "loading" : feedDone && blogs.length ? "done" : ""); }
  function maybeLoadMore() {
    const sentinel = $("feedSentinel");
    if (!sentinel || feedDone || feedLoading || feedError || $("latest-stories").hidden) return;
    if (sentinel.getBoundingClientRect().top < window.innerHeight + 700) loadMore();
  }
  async function loadMore() {
    if (feedLoading || feedDone || feedError) return;
    const ticket = feedTicket;
    feedLoading = true; syncFeedEnd();
    try {
      const batch = await fetchBatch(nextCursor);
      if (ticket !== feedTicket) return;
      const have = new Set(blogs.map(b => Number(blogId(b))));
      blogs = blogs.concat(batch.filter(b => !have.has(Number(blogId(b)))));
      if (batch.length) nextCursor = Number(blogId(batch[batch.length - 1]));
      feedDone = batch.length < BATCH;
      feedLoading = false;
      renderBlogs({ append: true });
    } catch {
      if (ticket !== feedTicket) return;
      feedLoading = false; feedError = true; syncFeedEnd();
    }
  }

  function openAuth(mode = "login") {
    authMode = mode;
    authReturnFocus = document.activeElement;
    updateAuthForm();
    $("authModal").classList.remove("hidden");
    setTimeout(() => $("authUsername").focus(), 50);
  }
  let authReturnFocus = null;
  function closeAuth() {
    $("authModal").classList.add("hidden");
    if (authReturnFocus && authReturnFocus.focus) authReturnFocus.focus();
  }
  $("authModal").setAttribute("role", "dialog");
  $("authModal").setAttribute("aria-modal", "true");
  $("authModal").addEventListener("keydown", (e) => {
    if (e.key === "Escape") { closeAuth(); return; }
    if (e.key !== "Tab") return;
    const items = [...$("authModal").querySelectorAll("button,input,a[href],select,textarea")].filter((el) => !el.disabled && el.offsetParent !== null);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });
  function updateAuthForm() {
    const registering = authMode === "register";
    $("authTitle").textContent = registering ? "Join the Journal." : "Welcome back.";
    $("authDescription").textContent = registering
      ? "Create an account and share what you are learning."
      : "Sign in to continue reading, writing and joining the conversation.";
    $("nameGroup").classList.toggle("hidden", !registering);
    $("emailGroup").classList.toggle("hidden", !registering);
    $("authName").required = registering;
    $("authEmail").required = registering;
    $("authPassword").autocomplete = registering ? "new-password" : "current-password";
    $("authSubmit").textContent = registering ? "Create account" : "Sign in";
    $("switchText").textContent = registering ? "Already a member?" : "New to Journal?";
    $("switchAuth").textContent = registering ? "Sign in" : "Create an account";
  }
  async function submitAuth(event) {
    event.preventDefault();
    const button = $("authSubmit");
    setBusy(button, true, authMode === "register" ? "Creating…" : "Signing in…");
    try {
      const username = $("authUsername").value.trim();
      const password = $("authPassword").value;
      if (authMode === "register") {
        await api("/user", {
          method: "POST",
          body: JSON.stringify({
            name: $("authName").value.trim(),
            username,
            email: $("authEmail").value.trim(),
            password
          })
        });
        showToast("Account created. Sign in with your new details.");
        authMode = "login";
        updateAuthForm();
        $("authPassword").value = "";
      } else {
        const form = new URLSearchParams();
        form.set("username", username);
        form.set("password", password);
        const response = await fetch(API_BASE + "/token", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: form
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || "Invalid username or password.");
        if (!data.access_token) throw new Error("The API did not return an access token.");
        token = data.access_token;
        store.set("access_token", token);
        await loadMe();
        closeAuth();
        updateNav();
        showToast("Welcome to Journal.");
        if (!$("latest-stories").hidden) await refreshBlogs();
        if (pendingWrite) { pendingWrite = false; openEditor(); }
      }
    } catch (error) {
      showToast(error.message);
    } finally {
      setBusy(button, false);
      // Button text is set from the current mode after mode transitions.
      if (!$("authModal").classList.contains("hidden")) $("authSubmit").textContent = authMode === "register" ? "Create account" : "Sign in";
    }
  }
  let pendingWrite = false;
  let editingId = null; // blog id while editing a story, null while writing a new one

  function setEditorMode(editing) {
    $("editorHeading").textContent = editing ? "Edit your story." : "Share a story.";
    $("publishButton").textContent = editing ? "Save changes" : "Publish story";
  }
  function openEditStory() {
    if (!currentBlog) return;
    editingId = blogId(currentBlog);
    $("editorCategory").value = categoryOf(currentBlog);
    $("editorTitle").value = plain(currentBlog.title).trim();
    $("editorContent").value = storyText(currentBlog).trim();
    $("editorContent").dispatchEvent(new Event("input"));
    setEditorMode(true);
    $("articlePage").classList.add("hidden");
    $("latest-stories").hidden = false;
    $("editorPanel").classList.remove("hidden");
    setWriting(true);
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function openEditor() {
    if (!token || !currentUser) {
      pendingWrite = true;
      openAuth("login");
      return;
    }
    if (editingId !== null) { editingId = null; $("editorForm").reset(); setEditorMode(false); }
    $("latest-stories").hidden = false;
    $("articlePage").classList.add("hidden");
    $("editorPanel").classList.remove("hidden");
    setWriting(true);
    window.scrollTo({ top: 0, behavior: "auto" });
    $("editorTitle").focus({ preventScroll: true });
  }
  async function publishStory(event) {
    event.preventDefault();
    if (!token) { openAuth("login"); return; }
    const title = $("editorTitle").value.trim();
    const content = $("editorContent").value.trim();
    const category = $("editorCategory").value;
    if (!title || !content) return showToast("Please add both a title and your story.");
    if (!category) return showToast("Please choose a category.");
    const button = $("publishButton");
    setBusy(button, true, "Publishing…");
    try {
      if (editingId !== null) {
        await api(`/blog/${editingId}`, {
          method: "PATCH",
          body: JSON.stringify({ title, content, category })
        });
      } else {
        await api("/blog", {
          method: "POST",
          body: JSON.stringify({ title, content: `[[category:${category}]]\n\n${content}` })
        });
      }
      const wasEditing = editingId !== null;
      editingId = null;
      setEditorMode(false);
      $("editorForm").reset();
      $("wordCount").textContent = "0 words";
      $("editorPanel").classList.add("hidden");
      showToast(wasEditing ? "Your story was updated." : "Your story is now published.");
      searchTerm = ""; activeFilter = "All"; $("blogQuery").value = "";
      await refreshBlogs();
      showStories();
    } catch (error) {
      showToast(error.message);
    } finally {
      setBusy(button, false);
    }
  }

  async function openArticle(id) {
    if (!$("latest-stories").hidden) listScroll = window.scrollY;
    $("articlePage").classList.remove("hidden");
    $("latest-stories").hidden = true;
    $("editorPanel").classList.add("hidden");
    setWriting(false);
    if (location.hash !== `#story-${id}`) { try { history.pushState({ journalPage: "story" }, "", `#story-${id}`); } catch {} }
    $("articleTitle").textContent = "Loading story…";
    $("articleContent").textContent = "";
    $("articleMeta").textContent = "";
    $("commentsList").textContent = "Loading conversation…";
    window.scrollTo({ top: 0, behavior: "smooth" });
    try {
      const blog = await api(`/blog/${id}`);
      currentBlog = blog;
      const shownTitle = plain(blog.title).trim();
      $("articleTitle").innerHTML = bidi(esc(shownTitle || "Untitled story"));
      document.querySelector(".article-kicker").textContent = categoryOf(blog);
      $("articleContent").textContent = withoutTitle(plain(storyText(blog)), shownTitle);
      $("articleMeta").textContent = `By ${authorName(blog) || "Journal member"}`;
      const ownStory = currentUser && String(userId(currentUser)) === String(blog.author_id);
      $("deleteButton").classList.toggle("hidden", !ownStory);
      $("editButton").classList.toggle("hidden", !ownStory);
      updateArticleActions();
      await loadComments(id);
    } catch (error) {
      $("articleTitle").textContent = "This story could not be opened.";
      $("articleContent").textContent = error.message;
    }
  }
  function updateArticleActions() {
    if (!currentBlog) return;
    const id = String(blogId(currentBlog));
    const author = String(currentBlog.author_id);
    $("likeButton").textContent = likedBlogs.has(id) ? "♥ Liked" : "♡ Like";
    $("likeButton").setAttribute("aria-pressed", String(likedBlogs.has(id)));
    $("followButton").textContent = followedUsers.has(author) ? "Following" : "Follow author";
    // Authors see Delete on their own story; everyone else sees Follow.
    const ownStory = !!currentUser && String(userId(currentUser)) === author;
    $("deleteButton").classList.toggle("hidden", !ownStory);
    $("editButton").classList.toggle("hidden", !ownStory);
    $("followButton").classList.toggle("hidden", ownStory);
  }
  async function loadComments(id) {
    try {
      const comments = await api(`/blog/${id}/comments`);
      if (!Array.isArray(comments) || !comments.length) {
        $("commentsList").innerHTML = `<p class="app-status">No comments yet. Start the conversation.</p>`;
        return;
      }
      $("commentsList").innerHTML = comments.map(comment =>
        `<div class="comment-item"><b>${esc(comment.commenter_name || comment.username || comment.author_name || "Journal member")}</b><p>${esc(comment.text || "")}</p></div>`
      ).join("");
    } catch (error) {
      $("commentsList").innerHTML = `<p class="app-status">${esc(error.message)}</p>`;
    }
  }
  async function postComment(event) {
    event.preventDefault();
    if (!token) { openAuth("login"); return; }
    if (!currentBlog) return;
    const input = $("commentInput");
    const text = input.value.trim();
    if (!text) return;
    try {
      await api(`/blog/${blogId(currentBlog)}/comment`, {
        method: "POST",
        body: JSON.stringify({ text })
      });
      input.value = "";
      showToast("Comment posted.");
      await loadComments(blogId(currentBlog));
    } catch (error) { showToast(error.message); }
  }
  async function toggleLike() {
    if (!token) { openAuth("login"); return; }
    if (!currentBlog) return;
    const id = String(blogId(currentBlog));
    try {
      if (likedBlogs.has(id)) {
        await api(`/blog/${id}/like`, { method: "DELETE" });
        likedBlogs.delete(id);
        showToast("Like removed.");
      } else {
        try {
          await api(`/blog/${id}/like`, { method: "POST" });
        } catch (error) {
          if (error.status === 400 && /already liked/i.test(error.message)) {
            likedBlogs.add(id);
            saveLocalActionState();
            updateArticleActions();
            return showToast("You already liked this story.");
          }
          throw error;
        }
        likedBlogs.add(id);
        showToast("You liked this story.");
      }
      saveLocalActionState();
      updateArticleActions();
    } catch (error) { showToast(error.message); }
  }
  async function toggleFollow() {
    if (!token) { openAuth("login"); return; }
    if (!currentBlog) return;
    const author = String(currentBlog.author_id);
    try {
      if (followedUsers.has(author)) {
        await api(`/user/${author}/follow`, { method: "DELETE" });
        followedUsers.delete(author);
        showToast("You unfollowed this author.");
      } else {
        try {
          await api(`/user/${author}/follow`, { method: "POST" });
        } catch (error) {
          if (error.status === 400 && /already following/i.test(error.message)) {
            followedUsers.add(author);
            saveLocalActionState();
            updateArticleActions();
            return showToast("You already follow this author.");
          }
          throw error;
        }
        followedUsers.add(author);
        showToast("You are now following this author.");
      }
      saveLocalActionState();
      updateArticleActions();
    } catch (error) { showToast(error.message); }
  }
  async function deleteStory() {
    if (!currentBlog || !confirm("Delete this story permanently?")) return;
    try {
      await api(`/blog/${blogId(currentBlog)}`, { method: "DELETE" });
      currentBlog = null;
      showToast("Your story has been deleted.");
      await refreshBlogs();
      showStories({ query: searchTerm });
    } catch (error) { showToast(error.message); }
  }

  // Event bindings
  $("navLatest").addEventListener("click", async () => { showStories(); await refreshBlogs(); });
  $("navWrite").addEventListener("click", async () => { if (!$("latest-stories").hidden) { /* already on stories screen */ } else { showStories(); await refreshBlogs(); } openEditor(); });
  $("authNavButton").addEventListener("click", () => token && currentUser ? showToast(`Signed in as ${currentUser.username}`) : openAuth("login"));
  $("signOutButton").addEventListener("click", () => {
    clearSession(); updateNav(); showToast("You have signed out.");
    if (!$("articlePage").classList.contains("hidden") || !$("editorPanel").classList.contains("hidden")) { showStories({ query: searchTerm }); if (!blogs.length) refreshBlogs(); }
  });
  $("homeLogo").addEventListener("click", showHome);
  const storyDoor = document.querySelector(".story-door");
  if (storyDoor) storyDoor.addEventListener("click", async e => { e.preventDefault(); showStories(); await refreshBlogs(); });
  window.addEventListener("popstate", () => {
    const storyHash = location.hash.match(/^#story-(.+)$/);
    if (storyHash) { showStories({ query: searchTerm, navigate: false }); openArticle(storyHash[1]); return; }
    if (location.hash === "#stories") { showStories({ query: searchTerm, navigate: false }); if (!blogs.length) refreshBlogs(); }
    else showHome({ navigate: false });
  });
  document.querySelectorAll("[data-go]").forEach(el => el.addEventListener("click", async () => { showStories(); await refreshBlogs(); }));
  $("sf").addEventListener("submit", async e => {
    e.preventDefault();
    showStories({ query: $("q").value });
    await refreshBlogs();
  });
  $("blogSearch").addEventListener("submit", async e => { e.preventDefault(); searchTerm = $("blogQuery").value.trim(); await refreshBlogs(); });
  $("grid").addEventListener("click", e => {
    const button = e.target.closest("[data-open-blog]");
    if (button) openArticle(button.getAttribute("data-open-blog"));
  });
  $("grid").addEventListener("error", e => { if (e.target.tagName === "IMG") e.target.closest(".media")?.remove(); }, true);
  $("chips").addEventListener("click", e => {
    const button = e.target.closest("[data-filter]");
    if (!button) return;
    activeFilter = button.getAttribute("data-filter");
    refreshBlogs();
  });
  $("editorForm").addEventListener("submit", publishStory);
  $("editorContent").addEventListener("input", e => {
    const words = e.target.value.trim() ? e.target.value.trim().split(/\s+/).length : 0;
    $("wordCount").textContent = `${words} words`;
  });
  $("cancelEditor").addEventListener("click", () => { editingId = null; setEditorMode(false); $("editorForm").reset(); $("editorPanel").classList.add("hidden"); setWriting(false); });
  $("feedEnd").addEventListener("click", (e) => { if (e.target.closest("#feedRetry")) { feedError = false; loadMore(); } });
  if ("IntersectionObserver" in window) {
    new IntersectionObserver((entries) => { if (entries.some(en => en.isIntersecting)) maybeLoadMore(); }, { rootMargin: "700px 0px" }).observe($("feedSentinel"));
  } else {
    window.addEventListener("scroll", maybeLoadMore, { passive: true });
  }
  $("backToStories").addEventListener("click", async () => {
    if (/^#story-/.test(location.hash)) { try { history.pushState({ journalPage: "stories" }, "", "#stories"); } catch {} }
    showStories({ query: searchTerm }); if (!blogs.length) await refreshBlogs(); // keep the loaded feed and your place in it
  });
  $("commentForm").addEventListener("submit", postComment);
  $("likeButton").addEventListener("click", toggleLike);
  $("followButton").addEventListener("click", toggleFollow);
  $("editButton").addEventListener("click", openEditStory);
  $("deleteButton").addEventListener("click", deleteStory);
  $("closeAuth").addEventListener("click", () => { pendingWrite = false; closeAuth(); });
  $("authModal").addEventListener("click", e => { if (e.target === $("authModal")) closeAuth(); });
  $("switchAuth").addEventListener("click", () => { authMode = authMode === "login" ? "register" : "login"; updateAuthForm(); });
  $("authForm").addEventListener("submit", submitAuth);
  // Menu drawer: used on every page (the header collapses into it on phones).
  const sideNav = $("sideNav"), sideBackdrop = $("sideBackdrop"), sideMenu = document.querySelector(".menu-btn");
  async function goTopic(category) { activeFilter = category; showStories(); await refreshBlogs(); }
  function setSide(open) {
    const wasOpen = sideNav.classList.contains("open");
    sideNav.classList.toggle("open", open);
    sideNav.setAttribute("aria-hidden", String(!open));
    sideBackdrop.hidden = !open;
    sideMenu.setAttribute("aria-expanded", String(open));
    if (!open) { if (wasOpen) sideMenu.focus(); return; }
    $("sideAuth").textContent = currentUser ? "Sign out" : "Sign in";
    const box = $("sideTopics");
    box.innerHTML = "";
    const onStories = document.body.classList.contains("stories-page");
    ["All", ...CATEGORIES].forEach((name) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = name;
      b.setAttribute("aria-pressed", String(onStories && activeFilter === name));
      b.addEventListener("click", () => { setSide(false); goTopic(name); });
      box.appendChild(b);
    });
    sideNav.querySelector(".side-close").focus();
  }
  sideMenu.addEventListener("click", () => setSide(true));
  sideBackdrop.addEventListener("click", () => setSide(false));
  sideNav.querySelector(".side-close").addEventListener("click", () => setSide(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && sideNav.classList.contains("open")) setSide(false); });
  sideNav.querySelectorAll("[data-side]").forEach((btn) => btn.addEventListener("click", () => {
    const act = btn.getAttribute("data-side");
    setSide(false);
    if (act === "home") $("homeLogo").click();
    else if (act === "write") $("navWrite").click();
    else if (act === "theme") $("theme").click();
    else if (act === "auth") $(currentUser ? "signOutButton" : "authNavButton").click();
    else if (act === "all") goTopic("All");
  }));

  // Theme: use the saved choice, else follow the system, so the stories page and home page always agree.
  (function initTheme() {
    const root = document.documentElement;
    if (root.getAttribute("data-theme")) return;
    const saved = store.get("journal_theme");
    const dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.setAttribute("data-theme", saved === "light" || saved === "dark" ? saved : (dark ? "dark" : "light"));
  })();
  $("theme").addEventListener("click", () => {
    const root = document.documentElement;
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const current = root.getAttribute("data-theme") || (systemDark ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    store.set("journal_theme", next);
    $("theme").blur(); // drop the focus ring left on the button after a mouse click
  });

  // Site footer: reuses the existing nav buttons so no navigation logic is duplicated.
  function initSiteFooter() {
    const footer = document.querySelector(".site-footer");
    if (!footer) return;
    const targets = { latest: "navLatest", write: "navWrite", signin: "authNavButton", signout: "signOutButton" };
    footer.addEventListener("click", (e) => {
      const el = e.target.closest("[data-footer-action]");
      const target = el && $(targets[el.dataset.footerAction]);
      if (target) target.click();
    });

    // Show Sign in or Sign out to match the header (follows the header's hidden class).
    const header = $("signOutButton");
    const syncAccount = () => {
      const signedIn = !header.classList.contains("hidden");
      footer.querySelectorAll('[data-footer-when="in"]').forEach(el => { el.hidden = !signedIn; });
      footer.querySelectorAll('[data-footer-when="out"]').forEach(el => { el.hidden = signedIn; });
    };
    syncAccount();
    new MutationObserver(syncAccount).observe(header, { attributes: true, attributeFilter: ["class"] });

    // Back to top
    $("sfTop").addEventListener("click", () => {
      const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: calm ? "auto" : "smooth" });
      $("homeLogo").focus({ preventScroll: true });
    });
  }
  initSiteFooter();

  // Initial session restoration. Blog content is fetched only when the stories
  // section is opened, so the artwork-led homepage stays exactly as designed.
  updateAuthForm();
  const initialStory = location.hash.match(/^#story-(.+)$/);
  if (location.hash === "#stories" || initialStory) showStories({ navigate: false });
  loadMe().then(() => { if (initialStory) openArticle(initialStory[1]); else if (location.hash === "#stories") refreshBlogs(); });
})();
