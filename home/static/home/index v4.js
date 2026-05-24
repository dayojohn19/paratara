/* =========================
   Utils
========================= */

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const slugify = (text) =>
  text.toLowerCase().trim().replace(/\s+/g, "-");

const confirmOpen = (label, url) => {
  const input = prompt("", `Check ${label}`);
  if (input === `Check ${label}`) {
    window.open(url, "_blank");
  }
};

const backgroundObserver = window.IntersectionObserver
  ? new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        loadPlaceBackground(entry.target);
        backgroundObserver.unobserve(entry.target);
      });
    }, { rootMargin: "220px 0px", threshold: 0.1 })
  : null;

function loadPlaceBackground(card) {
  const imageUrl = card.dataset.bg;
  if (!imageUrl || card.classList.contains("loaded-bg")) return;

  const img = new Image();
  img.src = imageUrl;
  img.onload = () => {
    card.style.backgroundImage = `url(${imageUrl})`;
    card.classList.remove("placeholder");
    card.classList.add("loaded-bg");
  };
  img.onerror = () => {
    card.style.backgroundImage = "linear-gradient(135deg, rgba(148, 163, 184, 0.16), rgba(148, 163, 184, 0.08))";
    card.classList.remove("placeholder");
    card.classList.add("loaded-bg");
  };
}

function observeCardBackground(card) {
  if (backgroundObserver) {
    backgroundObserver.observe(card);
  } else {
    loadPlaceBackground(card);
  }
}

const getCurrentMonthYear = () => {
  const now = new Date();
  return {
    day: now.getDate(),
    month: now.getMonth() + 1,
    year: now.getFullYear()
  };
};

/* =========================
   Navigation
========================= */

function openInNewTab(place, placeID) {
  let { day, month, year } = getCurrentMonthYear();
  const placeSlug = slugify(place);
  const url = `/${placeSlug}/place/${placeID}/${month}/${year}/`;
  window.open(url, "_blank");
  // confirmOpen(place, url);
}

function newTabPlaceSearch(placeName) {
  console.log('aa')
  let { day, month, year } = getCurrentMonthYear();
  const placeSlug = slugify(placeName);
  // const url = `/${placeSlug}/place/${month}/${year}/`;  
  const url = `/placeslug/${placeSlug}/`;  
  window.open(url, "_blank");
  // confirmOpen(placeName, `/placeslug/${slugify(placeName)}/`);
}

function changeSearchInputValue(value) {
  const input = document.querySelector(".where-to-go");
  if (input) input.value = value;
}

/* =========================
   Fetch & Render
========================= */

let allPlaces = [];
let currentPage = 1;
const itemsPerPage = 5;
let isLoadingPage = false;

async function getCarpoolJSON() {
  try {
    const response = await fetch(
      `${window.location.origin}/home/getcarpooljson/`,
      { headers: { Accept: "application/json" } }
    );

    const { PlacesList = [] } = await response.json();

    allPlaces = PlacesList;
    FilterPlacesEachType(); // Populate dropdown initially
    await renderPage(1);
    attachInfiniteScroll();

  } catch (error) {
    console.error("Carpool fetch failed:", error);
  }
}

async function renderPage(page = 1) {
  const container = document.querySelector(".container-list");
  if (!container) return;

  const totalPages = Math.max(1, Math.ceil(allPlaces.length / itemsPerPage));
  const nextPage = Math.min(Math.max(page, 1), totalPages);
  if (nextPage <= currentPage && nextPage !== 1) return;

  currentPage = nextPage;
  const pagePlaces = allPlaces.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  if (pagePlaces.length === 0) {
    toggleLandingMessage();
    return;
  }

  isLoadingPage = true;
  await renderPlacesSlowly(pagePlaces);
  isLoadingPage = false;
}

function getTotalPages() {
  return Math.max(1, Math.ceil(allPlaces.length / itemsPerPage));
}

function attachInfiniteScroll() {
  const onScroll = async () => {
    if (isLoadingPage) return;

    const scrollPosition = window.innerHeight + window.pageYOffset;
    const threshold = document.body.offsetHeight - 300;

    if (scrollPosition >= threshold && currentPage < getTotalPages()) {
      await renderPage(currentPage + 1);
    }
  };

  window.addEventListener("scroll", onScroll, { passive: true });
}

/* =========================
   Search Dropdown
========================= */

function renderSearchDropdown(places) {
  // Initial render is empty, will be populated on filter
}

/* =========================
   Main Place Cards
========================= */

async function renderPlacesSlowly(places) {
  const container = document.querySelector(".container-list");
  if (!container) return;

  for (const place of places) {
    const card = createPlaceCard(place);
    container.appendChild(card);
    observeCardBackground(card);
    toggleLandingMessage();
    await delay(10);
  }
}

function createPlaceCard(place) {
  const card = document.createElement("div");
  card.className = "container-item placeholder";
  card.dataset.episode = `${place.reviewCount} reviews`;
  card.dataset.place = place.placename;
  card.dataset.bg = place.placePhoto;
  card.style.backgroundImage = "linear-gradient(135deg, rgba(255, 255, 255, 0.72), rgba(241, 245, 249, 0.82))";

  card.addEventListener("click", () =>
    openInNewTab(place.placename, place.placeID)
  );

  const title = document.createElement("div");
  title.className = `container-title translateCenter item-${place.placeID}`;
  title.innerHTML = `<p class="placenametitle">${place.placename}</p>`;

  card.appendChild(title);
  return card;
}

/* =========================
   Filter
========================= */

function FilterPlacesEachType() {
  const input = document.getElementById("place_input_id_for_filter");
  const dropdown = document.getElementById("place_id_for_drop_down_filter");

  if (!input || !dropdown) return;

  const filter = input.value.toUpperCase().trim();
  if (!filter) {
    dropdown.innerHTML = "";
    hideDropdown();
    return;
  }

  const filteredPlaces = allPlaces.filter(place =>
    place.placename.toUpperCase().includes(filter)
  ).slice(0, 50); // Limit to 50 for performance

  dropdown.innerHTML = "";

  filteredPlaces.forEach(place => {
    const link = document.createElement("a");
    link.className = "dropdown-item search-drop-down";
    link.textContent = place.placename;

    link.addEventListener("click", () => {
      newTabPlaceSearch(place.placename);
      changeSearchInputValue(place.placename);
      hideDropdown();
    });

    dropdown.appendChild(link);
  });

  if (filteredPlaces.length > 0) {
    showDropdown();
  } else {
    hideDropdown();
  }
}

/* =========================
   Dropdown
========================= */

function showDropdown() {
  const dropdown = document.getElementById("place_id_for_drop_down_filter");
  const backdrop = document.getElementById("dropdown-backdrop");
  if (dropdown) dropdown.classList.add("show");
  if (backdrop) backdrop.classList.add("show");
}

function hideDropdown() {
  const dropdown = document.getElementById("place_id_for_drop_down_filter");
  const backdrop = document.getElementById("dropdown-backdrop");
  if (dropdown) dropdown.classList.remove("show");
  if (backdrop) backdrop.classList.remove("show");
}

/* =========================
   Init
========================= */

function toggleLandingMessage() {
  const list = document.querySelector(".container-list");
  const landing = document.getElementById("landing-message");

  if (!landing || !list) return;

  // If list has items (excluding progress bar)
  const hasItems = [...list.children].some(
    el => !el.classList.contains("progress-fill")
  );

  landing.style.display = hasItems ? "none" : "block";
}

document.addEventListener("DOMContentLoaded", () => {
  getCarpoolJSON();
  toggleLandingMessage();

  // Hide dropdown on outside click
  document.addEventListener("click", (e) => {
    const input = document.getElementById("place_input_id_for_filter");
    const dropdown = document.getElementById("place_id_for_drop_down_filter");
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      hideDropdown();
    }
  });
});
