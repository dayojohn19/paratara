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

const getCurrentMonthYear = () => {
  const now = new Date();
  return {
    month: now.getMonth() + 1,
    year: now.getFullYear()
  };
};

/* =========================
   Navigation
========================= */

function openInNewTab(place, placeID) {
  let { month, year } = getCurrentMonthYear();
  const placeSlug = slugify(place);
  const url = `/${placeSlug}/place/${placeID}/${month}/${year}/`;
  window.open(url, "_blank");
  // confirmOpen(place, url);
}

function newTabPlaceSearch(placeName) {
  console.log('aa')
  let { month, year } = getCurrentMonthYear();
  const placeSlug = slugify(placeName);
  const url = `/${placeSlug}/place/${month}/${year}/`;  
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

async function getCarpoolJSON() {
  try {
    const response = await fetch(
      `${window.location.origin}/home/getcarpooljson/`,
      { headers: { Accept: "application/json" } }
    );

    const { PlacesList = [] } = await response.json();

    renderSearchDropdown(PlacesList);
    await renderPlacesSlowly(PlacesList.slice(0, 20));

  } catch (error) {
    console.error("Carpool fetch failed:", error);
  }
}

/* =========================
   Search Dropdown
========================= */

function renderSearchDropdown(places) {
  const dropdown = document.getElementById("place_id_for_drop_down_filter");
  if (!dropdown) return;

  dropdown.innerHTML = "";

  places.forEach(place => {
    const link = document.createElement("a");
    link.className = "dropdown-item search-drop-down";
    // link.href = "#about";
    link.textContent = place.placename;

    link.addEventListener("click", () => {
      newTabPlaceSearch(place.placename);
      changeSearchInputValue(place.placename);
    });

    dropdown.appendChild(link);
  });
}

/* =========================
   Main Place Cards
========================= */

async function renderPlacesSlowly(places) {
  const container = document.querySelector(".container-list");
  if (!container) return;

  for (const place of places) {
    container.appendChild(createPlaceCard(place));
    await delay(50);
  }
}

function createPlaceCard(place) {
  const card = document.createElement("div");
  card.className = "container-item";
  card.dataset.episode = `${place.reviewCount} reviews`;
  card.dataset.place = place.placename;
  card.style.backgroundImage = `url(${place.placePhoto})`;

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

  const filter = input.value.toUpperCase();
  const items = dropdown.getElementsByClassName("search-drop-down");

  Array.from(items).forEach(item => {
    item.style.display =
      item.textContent.toUpperCase().includes(filter) ? "" : "none";
  });
}

/* =========================
   Dropdown
========================= */

function OpenDropDownForPlaces() {
  document
    .getElementById("place_id_for_drop_down_filter")
    ?.classList.toggle("show");
}

/* =========================
   Init
========================= */

document.addEventListener("DOMContentLoaded", getCarpoolJSON);
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
toggleLandingMessage();

document.addEventListener("DOMContentLoaded", toggleLandingMessage);
