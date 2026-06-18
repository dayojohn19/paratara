const API_ENDPOINT = "/home/getcarpooljson/";
const BLOG_ENDPOINT = "/home/random-blogs/";
const SEARCH_DEBOUNCE_MS = 180;

const slugify = (text) =>
  String(text || "")
    .toLowerCase()
    .trim()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

const state = {
  cardPlaces: [],
  currentPage: 0,
  itemsPerPage: 8,
  isLoadingPage: false,
  activeSearchIndex: -1,
  searchItems: [],
  popularSearchItems: null,
  searchRequestId: 0,
  searchTimer: null,
  destinationLoading: false,
  destinationLoaded: false,
  randomBlogsLoaded: false
};

const elements = {
  list: null,
  sentinel: null,
  landing: null,
  input: null,
  dropdown: null,
  backdrop: null,
  searchContainer: null,
  loadDestinations: null,
  status: null,
  locationButton: null,
  randomBlogs: null,
  authModal: null
};

let authPreviousFocus = null;

const backgroundObserver = window.IntersectionObserver
  ? new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        loadPlaceBackground(entry.target);
        backgroundObserver.unobserve(entry.target);
      });
    }, { rootMargin: "260px 0px", threshold: 0.01 })
  : null;

let sentinelObserver = null;

function cacheElements() {
  elements.list = document.getElementById("placesList");
  elements.sentinel = document.getElementById("placesSentinel");
  elements.landing = document.getElementById("landing-message");
  elements.input = document.getElementById("place_input_id_for_filter");
  elements.dropdown = document.getElementById("place_id_for_drop_down_filter");
  elements.backdrop = document.getElementById("dropdown-backdrop");
  elements.searchContainer = document.getElementById("placeSearchContainer");
  elements.loadDestinations = document.getElementById("loadDestinations");
  elements.status = document.getElementById("status");
  elements.locationButton = document.getElementById("get-loc");
  elements.randomBlogs = document.getElementById("homeRandomBlogs");
  elements.authModal = document.getElementById("homeAuthModal");
}

function getReviewCount(place) {
  const value = Number(place && place.reviewCount);
  return Number.isFinite(value) ? value : 0;
}

function getPlaceUrl(place) {
  const slug = place && place.slug ? place.slug : slugify(place && place.placename);
  return slug ? `/placeslug/${slug}/` : "/";
}

function buildPlacesUrl(options = {}) {
  const params = new URLSearchParams();
  const limit = Number(options.limit);

  if (options.lite) params.set("lite", "1");
  if (options.query) params.set("q", options.query);
  if (Number.isFinite(limit) && limit > 0) params.set("limit", String(limit));

  const queryString = params.toString();
  return queryString ? `${API_ENDPOINT}?${queryString}` : API_ENDPOINT;
}

async function fetchPlaces(options = {}) {
  const response = await fetch(buildPlacesUrl(options), {
    headers: { Accept: "application/json" }
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const { PlacesList = [] } = await response.json();
  return Array.isArray(PlacesList) ? PlacesList : [];
}

function changeSearchInputValue(value) {
  if (elements.input) elements.input.value = value;
}

function showDropdown() {
  if (elements.searchContainer) elements.searchContainer.setAttribute("aria-expanded", "true");
}

function hideDropdown() {
  if (elements.searchContainer) elements.searchContainer.setAttribute("aria-expanded", "false");
  if (elements.input) elements.input.removeAttribute("aria-activedescendant");
}

function showDropdownMessage(message, className = "dropdown-empty") {
  if (!elements.dropdown) return;

  const node = document.createElement("div");
  node.className = className;
  node.textContent = message;
  elements.dropdown.replaceChildren(node);
}

async function renderSearchDropdown(options = {}) {
  if (!elements.input || !elements.dropdown) return;

  const filter = elements.input.value.trim();
  const requestId = state.searchRequestId + 1;
  state.searchRequestId = requestId;

  if (options.open) {
    showDropdown();
    showDropdownMessage("Loading destinations...", "dropdown-loading");
  }

  if (!filter && state.popularSearchItems) {
    renderSearchResults(state.popularSearchItems, filter, options.open);
    return;
  }

  try {
    const places = await fetchPlaces({
      lite: true,
      query: filter,
      limit: filter ? 12 : 8
    });

    if (requestId !== state.searchRequestId) return;
    if (!filter) state.popularSearchItems = places;
    renderSearchResults(places, filter, options.open);
  } catch (error) {
    if (requestId !== state.searchRequestId) return;
    showDropdownMessage("Destinations could not load.");
    console.error("Destination search failed:", error);
  }
}

function renderSearchResults(places, filter, shouldOpen) {
  if (!elements.dropdown) return;

  const visibleMatches = places.slice(0, filter ? 12 : 8);
  state.searchItems = visibleMatches;
  state.activeSearchIndex = visibleMatches.length ? 0 : -1;
  elements.dropdown.innerHTML = "";

  if (!visibleMatches.length) {
    showDropdownMessage("No destinations found.");
    if (shouldOpen) showDropdown();
    return;
  }

  if (!filter) {
    const label = document.createElement("div");
    label.className = "dropdown-section-label";
    label.textContent = "Popular destinations";
    elements.dropdown.appendChild(label);
  }

  visibleMatches.forEach((place, index) => {
    const link = document.createElement("a");
    link.className = "dropdown-item search-drop-down";
    link.href = getPlaceUrl(place);
    link.id = `place-option-${index}`;
    link.role = "option";
    link.setAttribute("aria-selected", index === state.activeSearchIndex ? "true" : "false");

    if (index === state.activeSearchIndex) {
      link.classList.add("active");
    }

    const name = document.createElement("span");
    appendHighlightedText(name, place.placename || "Destination", filter);

    const meta = document.createElement("span");
    meta.className = "dropdown-meta";
    meta.textContent = `${getReviewCount(place)} reviews`;

    link.appendChild(name);
    link.appendChild(meta);
    link.addEventListener("click", (event) => {
      event.preventDefault();
      chooseSearchPlace(index);
    });

    elements.dropdown.appendChild(link);
  });

  syncActiveSearchItem();
  if (shouldOpen) showDropdown();
}

function appendHighlightedText(parent, text, filter) {
  if (!filter) {
    parent.textContent = text;
    return;
  }

  const lowerText = text.toLowerCase();
  const lowerFilter = filter.toLowerCase();
  const start = lowerText.indexOf(lowerFilter);

  if (start === -1) {
    parent.textContent = text;
    return;
  }

  parent.appendChild(document.createTextNode(text.slice(0, start)));
  const mark = document.createElement("mark");
  mark.textContent = text.slice(start, start + filter.length);
  parent.appendChild(mark);
  parent.appendChild(document.createTextNode(text.slice(start + filter.length)));
}

function chooseSearchPlace(index) {
  const place = state.searchItems[index];
  if (!place) return;
  changeSearchInputValue(place.placename || "");
  hideDropdown();
  window.location.assign(getPlaceUrl(place));
}

function moveActiveSearchItem(direction) {
  if (!state.searchItems.length) return;
  state.activeSearchIndex =
    (state.activeSearchIndex + direction + state.searchItems.length) % state.searchItems.length;
  syncActiveSearchItem();
}

function syncActiveSearchItem() {
  if (!elements.dropdown || !elements.input) return;

  elements.dropdown.querySelectorAll(".dropdown-item").forEach((item, index) => {
    const isActive = index === state.activeSearchIndex;
    item.classList.toggle("active", isActive);
    item.setAttribute("aria-selected", isActive ? "true" : "false");
    if (isActive) {
      elements.input.setAttribute("aria-activedescendant", item.id);
      item.scrollIntoView({ block: "nearest" });
    }
  });
}

function queueSearchDropdown() {
  window.clearTimeout(state.searchTimer);
  state.searchTimer = window.setTimeout(() => {
    renderSearchDropdown({ open: true });
  }, SEARCH_DEBOUNCE_MS);
}

function bindSearchEvents() {
  if (!elements.input || !elements.dropdown) return;

  elements.input.addEventListener("input", queueSearchDropdown);
  elements.input.addEventListener("focus", () => renderSearchDropdown({ open: true }));
  elements.input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!state.searchItems.length) {
        renderSearchDropdown({ open: true });
        return;
      }
      moveActiveSearchItem(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveActiveSearchItem(-1);
    } else if (event.key === "Enter") {
      if (!state.searchItems.length) return;
      event.preventDefault();
      chooseSearchPlace(Math.max(state.activeSearchIndex, 0));
    } else if (event.key === "Escape") {
      hideDropdown();
      elements.input.blur();
    }
  });

  document.addEventListener("click", (event) => {
    if (elements.searchContainer && elements.searchContainer.contains(event.target)) return;
    hideDropdown();
  });
}

function revealDestinationList() {
  if (elements.list) elements.list.hidden = false;
}

function removeDestinationCards() {
  if (!elements.list) return;
  elements.list.querySelectorAll(".container-item, .home-state").forEach((item) => item.remove());
}

async function loadDestinationCards() {
  if (state.destinationLoading || state.destinationLoaded) return;
  if (!elements.list || !elements.sentinel) return;

  state.destinationLoading = true;
  revealDestinationList();
  setLoadButtonLoading(true);
  removeDestinationCards();
  showSkeletons();

  try {
    state.cardPlaces = await fetchPlaces({ limit: 48 });
    clearSkeletons();
    state.currentPage = 0;

    if (!state.cardPlaces.length) {
      showStateMessage("empty", "No destinations are available yet.", "New places will appear here when they are published.");
      return;
    }

    renderPage();
    attachInfiniteScroll();
    state.destinationLoaded = true;
    if (elements.loadDestinations) elements.loadDestinations.hidden = true;
  } catch (error) {
    clearSkeletons();
    showStateMessage("error", "Destinations could not load.", "Please refresh the page in a moment.");
    console.error("Destination cards failed:", error);
  } finally {
    state.destinationLoading = false;
    setLoadButtonLoading(false);
  }
}

function setLoadButtonLoading(isLoading) {
  if (!elements.loadDestinations) return;
  elements.loadDestinations.disabled = isLoading;
  elements.loadDestinations.textContent = isLoading ? "Loading destinations..." : "Browse destination cards";
}

function renderPage() {
  if (!elements.list || state.isLoadingPage) return;

  const totalPages = Math.ceil(state.cardPlaces.length / state.itemsPerPage);
  if (state.currentPage >= totalPages) return;

  state.isLoadingPage = true;
  const start = state.currentPage * state.itemsPerPage;
  const pagePlaces = state.cardPlaces.slice(start, start + state.itemsPerPage);
  const fragment = document.createDocumentFragment();

  pagePlaces.forEach((place) => {
    const card = createPlaceCard(place);
    fragment.appendChild(card);
  });

  elements.list.insertBefore(fragment, elements.sentinel);
  elements.list.querySelectorAll(".container-item:not([data-observed])").forEach((card) => {
    card.dataset.observed = "true";
    observeCardBackground(card);
  });

  state.currentPage += 1;
  state.isLoadingPage = false;
  toggleLandingMessage();
}

function attachInfiniteScroll() {
  if (!elements.sentinel) return;

  if (sentinelObserver) {
    sentinelObserver.disconnect();
  }

  if (window.IntersectionObserver) {
    sentinelObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) renderPage();
      });
    }, { rootMargin: "420px 0px", threshold: 0 });
    sentinelObserver.observe(elements.sentinel);
    return;
  }

  window.addEventListener("scroll", () => {
    const nearBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 360;
    if (nearBottom) renderPage();
  }, { passive: true });
}

function createPlaceCard(place) {
  const card = document.createElement("a");
  card.className = "container-item placeholder";
  card.href = getPlaceUrl(place);
  card.dataset.place = place.placename || "";
  card.dataset.bg = place.placePhoto || "";
  card.setAttribute("aria-label", `Open ${place.placename || "place"}`);

  const content = document.createElement("div");
  content.className = "container-title";

  const title = document.createElement("h3");
  title.className = "placenametitle";
  title.textContent = place.placename || "Destination";

  const footer = document.createElement("div");
  footer.className = "place-card-footer";

  const reviews = document.createElement("span");
  reviews.className = "place-review-count";
  reviews.textContent = `${getReviewCount(place)} reviews`;

  footer.appendChild(reviews);
  content.appendChild(title);
  content.appendChild(footer);
  card.appendChild(content);

  return card;
}

function loadPlaceBackground(card) {
  const imageUrl = card.dataset.bg;
  if (!imageUrl || card.classList.contains("loaded-bg")) {
    card.classList.remove("placeholder");
    return;
  }

  const img = new Image();
  img.decoding = "async";
  img.src = imageUrl;
  img.onload = () => {
    card.style.backgroundImage = `url("${imageUrl}")`;
    card.classList.remove("placeholder");
    card.classList.add("loaded-bg");
  };
  img.onerror = () => {
    card.classList.remove("placeholder");
  };
}

function observeCardBackground(card) {
  if (backgroundObserver) {
    backgroundObserver.observe(card);
  } else {
    loadPlaceBackground(card);
  }
}

function showSkeletons(count = 8) {
  if (!elements.list || !elements.sentinel) return;
  clearSkeletons();

  const fragment = document.createDocumentFragment();
  for (let i = 0; i < count; i += 1) {
    const skeleton = document.createElement("div");
    skeleton.className = "place-card-skeleton";
    skeleton.setAttribute("aria-hidden", "true");
    fragment.appendChild(skeleton);
  }

  elements.list.insertBefore(fragment, elements.sentinel);
  toggleLandingMessage();
}

function clearSkeletons() {
  if (!elements.list) return;
  elements.list.querySelectorAll(".place-card-skeleton").forEach((item) => item.remove());
}

function showStateMessage(type, title, message) {
  if (!elements.list || !elements.sentinel) return;
  elements.list.querySelectorAll(".home-state").forEach((item) => item.remove());

  const stateNode = document.createElement("div");
  stateNode.className = `home-state ${type || ""}`.trim();

  const heading = document.createElement("h2");
  heading.textContent = title;

  const copy = document.createElement("p");
  copy.textContent = message;

  stateNode.appendChild(heading);
  stateNode.appendChild(copy);
  elements.list.insertBefore(stateNode, elements.sentinel);
  toggleLandingMessage();
}

function toggleLandingMessage() {
  if (!elements.landing || !elements.list) return;
  const hasCards = elements.list.querySelector(".container-item");
  const hasState = elements.list.querySelector(".home-state");
  elements.landing.hidden = Boolean(hasCards || hasState);
}

function bindDestinationLoader() {
  if (!elements.loadDestinations) return;
  elements.loadDestinations.addEventListener("click", loadDestinationCards);
}

async function loadRandomBlogs() {
  if (!elements.randomBlogs || state.randomBlogsLoaded) return;

  state.randomBlogsLoaded = true;
  const endpoint = elements.randomBlogs.dataset.blogsEndpoint || BLOG_ENDPOINT;
  const separator = endpoint.includes("?") ? "&" : "?";

  try {
    const response = await fetch(`${endpoint}${separator}limit=7`, {
      headers: { Accept: "application/json" }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const blogs = Array.isArray(data.blogs) ? data.blogs.slice(0, 7) : [];
    renderRandomBlogs(blogs);
  } catch (error) {
    renderRandomBlogMessage("Guides could not load right now.");
    console.error("Random blogs failed:", error);
  }
}

function renderRandomBlogs(blogs) {
  if (!elements.randomBlogs) return;
  elements.randomBlogs.setAttribute("aria-busy", "false");

  if (!blogs.length) {
    renderRandomBlogMessage("Guides will appear here soon.");
    return;
  }

  const fragment = document.createDocumentFragment();
  blogs.forEach((blog) => {
    fragment.appendChild(createRandomBlogCard(blog));
  });
  elements.randomBlogs.replaceChildren(fragment);
}

function createRandomBlogCard(blog) {
  const card = document.createElement("a");
  card.className = "random-blog-card";
  card.href = blog.url || "#";
  card.setAttribute("aria-label", `Read ${blog.title || "travel guide"}`);

  const meta = document.createElement("span");
  meta.className = "random-blog-meta";
  const readtime = Number(blog.readtime);
  meta.textContent = [
    blog.place,
    blog.category || "Guide",
    Number.isFinite(readtime) && readtime > 0 ? `${readtime} min read` : ""
  ].filter(Boolean).join(" / ");

  const title = document.createElement("h3");
  title.textContent = blog.title || "Travel guide";

  const summary = document.createElement("p");
  summary.textContent = blog.summary || "Open a quick destination guide from Paratara.";

  card.appendChild(meta);
  card.appendChild(title);
  card.appendChild(summary);
  return card;
}

function renderRandomBlogMessage(message) {
  if (!elements.randomBlogs) return;
  elements.randomBlogs.setAttribute("aria-busy", "false");

  const stateNode = document.createElement("div");
  stateNode.className = "random-blog-state";
  stateNode.textContent = message;
  elements.randomBlogs.replaceChildren(stateNode);
}

function bindScheduleButtons() {
  document.querySelectorAll("[data-create-schedule]").forEach((button) => {
    button.addEventListener("click", () => {
      if (typeof window.createViaje === "function") {
        window.createViaje();
      }
    });
  });
}

function bindAuthModal() {
  if (!elements.authModal) return;

  document.querySelectorAll("[data-auth-open]").forEach((trigger) => {
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      openAuthModal(trigger.dataset.authOpen || "login", trigger);
    });
  });

  elements.authModal.querySelectorAll("[data-auth-close]").forEach((button) => {
    button.addEventListener("click", closeAuthModal);
  });

  elements.authModal.querySelectorAll("[data-auth-tab]").forEach((button) => {
    button.addEventListener("click", () => setAuthMode(button.dataset.authTab));
  });

  elements.authModal.querySelectorAll("[data-auth-form]").forEach((form) => {
    form.addEventListener("submit", submitAuthForm);
  });

  document.addEventListener("keydown", handleAuthModalKeydown);
}

function openAuthModal(mode, trigger) {
  if (!elements.authModal) return;

  authPreviousFocus = trigger || document.activeElement;
  setAuthMode(mode);
  elements.authModal.hidden = false;
  document.body.classList.add("auth-modal-open");

  window.requestAnimationFrame(() => {
    const activePanel = elements.authModal.querySelector(`[data-auth-panel="${mode}"]`);
    const firstInput = activePanel && activePanel.querySelector("input");
    const closeButton = elements.authModal.querySelector("[data-auth-close]");
    (firstInput || closeButton)?.focus();
  });
}

function closeAuthModal() {
  if (!elements.authModal || elements.authModal.hidden) return;

  elements.authModal.hidden = true;
  document.body.classList.remove("auth-modal-open");
  clearAuthStatuses();

  if (authPreviousFocus && typeof authPreviousFocus.focus === "function") {
    authPreviousFocus.focus();
  }
}

function setAuthMode(mode) {
  if (!elements.authModal) return;
  const selectedMode = mode === "register" ? "register" : "login";

  elements.authModal.querySelectorAll("[data-auth-tab]").forEach((button) => {
    const selected = button.dataset.authTab === selectedMode;
    button.classList.toggle("is-active", selected);
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
  });

  elements.authModal.querySelectorAll("[data-auth-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.authPanel !== selectedMode;
  });

  clearAuthStatuses();
}

function clearAuthStatuses() {
  if (!elements.authModal) return;
  elements.authModal.querySelectorAll("[data-auth-status]").forEach((status) => {
    status.textContent = "";
    status.classList.remove("is-success");
  });
}

function handleAuthModalKeydown(event) {
  if (!elements.authModal || elements.authModal.hidden) return;

  if (event.key === "Escape") {
    event.preventDefault();
    closeAuthModal();
    return;
  }

  if (event.key !== "Tab") return;

  const focusable = Array.from(
    elements.authModal.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  ).filter((item) => !item.closest("[hidden]"));

  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

async function submitAuthForm(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const mode = form.dataset.authForm;
  const status = form.querySelector("[data-auth-status]");
  const submitButton = form.querySelector('button[type="submit"]');
  const formData = new FormData(form);

  if (mode === "register" && formData.get("userPassword") !== formData.get("userPasswordConfirmation")) {
    setAuthStatus(status, "Passwords must match.");
    return;
  }

  const payload = mode === "register"
    ? {
        username: String(formData.get("userName") || "").trim(),
        contact: String(formData.get("userEmail") || "").trim(),
        password: String(formData.get("userPassword") || ""),
        passwordConfirmation: String(formData.get("userPasswordConfirmation") || ""),
        putname: String(formData.get("userName") || "").trim()
      }
    : {
        usernameJSON: String(formData.get("userName") || "").trim(),
        passwordJSON: String(formData.get("userPassword") || "")
      };

  submitButton.disabled = true;
  submitButton.textContent = mode === "register" ? "Creating account..." : "Logging in...";
  setAuthStatus(status, "");

  try {
    const response = await fetch(form.dataset.jsonEndpoint, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": formData.get("csrfmiddlewaretoken") || ""
      },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    const message = Array.isArray(data) ? data[0] : data;
    const loginFailed = mode === "login" && !Array.isArray(data);

    if (!response.ok || loginFailed) {
      throw new Error(message || "Authentication failed.");
    }

    setAuthStatus(status, mode === "register" ? "Account created. Opening Paratara..." : "Logged in. Opening Paratara...", true);
    window.setTimeout(() => window.location.reload(), 450);
  } catch (error) {
    setAuthStatus(status, error.message || "Please try again.");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = mode === "register" ? "Create account" : "Log in";
  }
}

function setAuthStatus(status, message, success = false) {
  if (!status) return;
  status.textContent = message;
  status.classList.toggle("is-success", success);
}

function bindFooterLocation() {
  if (!elements.locationButton || !elements.status) return;

  elements.locationButton.addEventListener("click", () => {
    if (!("geolocation" in navigator)) {
      elements.status.textContent = "Geolocation is not supported by your browser.";
      return;
    }

    elements.status.textContent = "Getting location...";
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const latitude = position.coords.latitude.toFixed(5);
        const longitude = position.coords.longitude.toFixed(5);
        elements.status.textContent = `Latitude: ${latitude}, Longitude: ${longitude}`;
      },
      (error) => {
        elements.status.textContent = `Error: ${error.message}`;
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  });
}

function FilterPlacesEachType() {
  renderSearchDropdown({ open: true });
}

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  bindSearchEvents();
  bindDestinationLoader();
  bindScheduleButtons();
  bindFooterLocation();
  bindAuthModal();
  window.setTimeout(loadRandomBlogs, 0);
  toggleLandingMessage();
});

window.FilterPlacesEachType = FilterPlacesEachType;
window.hideDropdown = hideDropdown;
