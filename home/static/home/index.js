const slugify = (text) =>
  String(text || "")
    .toLowerCase()
    .trim()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

const getCurrentMonthYear = () => {
  const now = new Date();
  return {
    month: now.getMonth() + 1,
    year: now.getFullYear()
  };
};

const state = {
  allPlaces: [],
  currentPage: 0,
  itemsPerPage: 8,
  isLoadingPage: false,
  activeSearchIndex: -1,
  searchItems: []
};

const elements = {
  list: null,
  sentinel: null,
  landing: null,
  input: null,
  dropdown: null,
  backdrop: null,
  searchContainer: null
};

const backgroundObserver = window.IntersectionObserver
  ? new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        loadPlaceBackground(entry.target);
        backgroundObserver.unobserve(entry.target);
      });
    }, { rootMargin: "240px 0px", threshold: 0.01 })
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
}

function openInNewTab(place, placeID) {
  const { month, year } = getCurrentMonthYear();
  const placeSlug = slugify(place);
  window.open(`/${placeSlug}/place/${placeID}/${month}/${year}/`, "_blank");
}

function newTabPlaceSearch(placeName) {
  window.open(`/placeslug/${slugify(placeName)}/`, "_blank");
}

function changeSearchInputValue(value) {
  if (elements.input) elements.input.value = value;
}

function getReviewCount(place) {
  const value = Number(place && place.reviewCount);
  return Number.isFinite(value) ? value : 0;
}

function sortedPlaces() {
  return [...state.allPlaces].sort((a, b) => {
    const reviews = getReviewCount(b) - getReviewCount(a);
    if (reviews !== 0) return reviews;
    return String(a.placename || "").localeCompare(String(b.placename || ""));
  });
}

function getPlaceUrl(place) {
  return `/placeslug/${slugify(place.placename)}/`;
}

async function getCarpoolJSON() {
  showSkeletons();

  try {
    const response = await fetch(`${window.location.origin}/home/getcarpooljson/`, {
      headers: { Accept: "application/json" }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const { PlacesList = [] } = await response.json();
    state.allPlaces = Array.isArray(PlacesList) ? PlacesList : [];

    clearSkeletons();
    if (!state.allPlaces.length) {
      showStateMessage("empty", "No destinations are available yet.", "New places will appear here when they are published.");
      return;
    }

    renderSearchDropdown();
    renderPage();
    attachInfiniteScroll();
  } catch (error) {
    clearSkeletons();
    showStateMessage("error", "Destinations could not load.", "Please refresh the page in a moment.");
    console.error("Carpool fetch failed:", error);
  }
}

function renderPage() {
  if (!elements.list || state.isLoadingPage) return;

  const totalPages = Math.ceil(state.allPlaces.length / state.itemsPerPage);
  if (state.currentPage >= totalPages) return;

  state.isLoadingPage = true;
  const start = state.currentPage * state.itemsPerPage;
  const pagePlaces = state.allPlaces.slice(start, start + state.itemsPerPage);
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
  const card = document.createElement("article");
  card.className = "container-item placeholder";
  card.tabIndex = 0;
  card.role = "button";
  card.dataset.place = place.placename || "";
  card.dataset.bg = place.placePhoto || "";
  card.setAttribute("aria-label", `Open ${place.placename || "place"}`);

  const open = () => openInNewTab(place.placename, place.placeID);
  card.addEventListener("click", open);
  card.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    open();
  });

  const content = document.createElement("div");
  content.className = "container-title";

  const title = document.createElement("h2");
  title.className = "placenametitle";
  title.textContent = place.placename || "Destination";

  const footer = document.createElement("div");
  footer.className = "place-card-footer";

  const reviews = document.createElement("span");
  reviews.className = "place-review-count";
  reviews.textContent = `${getReviewCount(place)} reviews`;

  // const action = document.createElement("span");
  // action.className = "place-card-action";
  // action.textContent = "Open";

  footer.appendChild(reviews);
  // footer.appendChild(action);
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

function renderSearchDropdown(options = {}) {
  if (!elements.input || !elements.dropdown) return;

  const shouldOpen = Boolean(options.open);
  const filter = elements.input.value.trim();
  const filterLower = filter.toLowerCase();
  const matches = filter
    ? state.allPlaces.filter((place) =>
        String(place.placename || "").toLowerCase().includes(filterLower)
      )
    : sortedPlaces();

  const visibleMatches = matches.slice(0, filter ? 50 : 8);
  state.searchItems = visibleMatches;
  state.activeSearchIndex = visibleMatches.length ? 0 : -1;
  elements.dropdown.innerHTML = "";

  if (!visibleMatches.length) {
    const empty = document.createElement("div");
    empty.className = "dropdown-empty";
    empty.textContent = "No destinations found.";
    elements.dropdown.appendChild(empty);
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
  newTabPlaceSearch(place.placename);
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

function FilterPlacesEachType() {
  renderSearchDropdown({ open: true });
}

function showDropdown() {
  if (elements.dropdown) elements.dropdown.classList.add("show");
  if (elements.backdrop) elements.backdrop.classList.add("show");
  if (elements.searchContainer) elements.searchContainer.setAttribute("aria-expanded", "true");
}

function hideDropdown() {
  if (elements.dropdown) elements.dropdown.classList.remove("show");
  if (elements.backdrop) elements.backdrop.classList.remove("show");
  if (elements.searchContainer) elements.searchContainer.setAttribute("aria-expanded", "false");
  if (elements.input) elements.input.removeAttribute("aria-activedescendant");
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

function bindSearchEvents() {
  if (!elements.input || !elements.dropdown) return;

  elements.input.addEventListener("input", () => renderSearchDropdown({ open: true }));
  elements.input.addEventListener("focus", () => renderSearchDropdown({ open: true }));
  elements.input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveActiveSearchItem(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveActiveSearchItem(-1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      chooseSearchPlace(Math.max(state.activeSearchIndex, 0));
    } else if (event.key === "Escape") {
      hideDropdown();
      elements.input.blur();
    }
  });

  if (elements.backdrop) {
    elements.backdrop.addEventListener("click", hideDropdown);
  }

  document.addEventListener("click", (event) => {
    if (elements.searchContainer && elements.searchContainer.contains(event.target)) return;
    hideDropdown();
  });
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

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  bindSearchEvents();
  bindScheduleButtons();
  getCarpoolJSON();
  toggleLandingMessage();
});

window.FilterPlacesEachType = FilterPlacesEachType;
window.hideDropdown = hideDropdown;
window.openInNewTab = openInNewTab;
window.newTabPlaceSearch = newTabPlaceSearch;
