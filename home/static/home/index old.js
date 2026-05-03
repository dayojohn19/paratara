function openInNewTab(place, placeID) {
  today = new Date();
  year = today.getFullYear();      // e.g. 2025
  month = today.getMonth() + 1;    // e.g. 10 (months are 0-indexed)
  date = today.getDate();     
// path("place/<int:id>/<int:currentMonth>/<int:currentYear>/",
  // const openURL = `/place/${place}`;
  placeURL = place.toLowerCase().replace(/\s+/g, "-");
  const openURL = `/${placeURL}/place/${placeID}/${month}/${year}`;
  const userInput = prompt("", `Check ${place}`);
  if (userInput === `Check ${place}`) {
    window.open(openURL, "_blank");
  }
}
function changeSearchInputValue(newInputValue) {
  const input = document.querySelector(".where-to-go");
  if (input) input.value = newInputValue;
}
function newTabPlaceSearch(placeName) {
  console.log("Place Name:", placeName);
  const userInput = prompt("", `Check ${placeName}`);
  if (userInput === `Check ${placeName}`) {
    window.open(`/place/${placeName}`, "_blank");
  }
}


 async function getCarpoolJSON() {
  try {
    const response = await fetch(`${window.location.origin}/home/getcarpooljson/`, {
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      }
    });
    const data = await response.json();

    // simple helper delay
    const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

    // populate search box
    function addToSearchBox(listToAddInSearchBox) {
      setTimeout(() => {
        const placeDataList = listToAddInSearchBox["PlacesList"];
        const searchBoxList = document.querySelector("#place_id_for_drop_down_filter");
        placeDataList.forEach((place) => {
          const newSearchItem = `
            <a class="dropdown-item search-drop-down" 
              onclick="newTabPlaceSearch('${place.placename}'); changeSearchInputValue('${place.placename}')"
              href="#about">${place.placename}</a>`;
          searchBoxList.innerHTML += newSearchItem;
        });
      }, 500);
    }
    addToSearchBox(data);

    // prepare to add items to main body
    const placeDataList = data["PlacesList"];
    const bodyContainer = document.querySelector(".container-list");
    if (!bodyContainer) return;

    window.bodyContainerList = bodyContainer;

    function slowAddToPage(item) {
      class CreateObjectOnLandingPageOfCarpool {
        constructor(placeItem) {
          this.objectMainContainer = document.createElement("div");
          this.objectMainContainer.setAttribute("data-episode", `${placeItem.reviewCount} reviews`);
          this.objectMainContainer.setAttribute("data-place", placeItem.placename);
          this.objectMainContainer.className = "container-item";
          this.objectMainContainer.style.backgroundImage =
            // `linear-gradient(to top, rgb(0, 0, 0), rgba(252, 180, 180, 0.29) 15.55%, rgba(0,0,0,0.32) 20.17%, rgba(0,0,0,0) 59.66%), url(${placeItem.placePhoto})`;
            `url(${placeItem.placePhoto})`
          this.objectMainContainer.setAttribute(
            "onclick",
            `openInNewTab('${placeItem.placename}','${placeItem.placeID}')`
          );

          this.objectSubContainer = document.createElement("div");
          this.objectSubContainer.className = `container-title translateCenter item-${placeItem.placeID}`;
          this.objectSubContainer.innerHTML = `<p class="placenametitle">${placeItem.placename}</p>`;

          this.objectMainContainer.appendChild(this.objectSubContainer);
          return this.objectMainContainer;
        }
      }

      bodyContainer.appendChild(new CreateObjectOnLandingPageOfCarpool(item));
    }

    // add them slowly with 50ms delay
    for (let i = 0; i < Math.min(20, placeDataList.length); i++) {
      slowAddToPage(placeDataList[i]);
      await delay(50); // 50ms delay per item
    }

  } catch (err) {
    console.error("Error in getCarpoolJSON:", err);
  }
}


function FilterPlacesEachType() {
  setTimeout(() => {
    const input = document.getElementById("place_input_id_for_filter");
    if (!input) return;

    const filter = input.value.toUpperCase();
    const dropdown = document.getElementById("place_id_for_drop_down_filter");
    if (!dropdown) return;

    const items = dropdown.getElementsByClassName("search-drop-down");
    Array.from(items).forEach((item) => {
      const txtValue = item.textContent || item.innerText;
      item.style.display = txtValue.toUpperCase().includes(filter) ? "" : "none";
    });
  }, 500);
}


document.addEventListener("DOMContentLoaded", () => {
  setTimeout(getCarpoolJSON, 500);
});




// Unused but preserved for consistency
function makePlacesFontSize(whatPlace, itsWidth) {
  const placeContainer = document.createElement("div");
  const words = whatPlace.split(" ");

  words.forEach((word) => {
    const fontContainer = document.createElement("div");
    if (word.length >= 6) {
      fontContainer.style.fontSize = "1.7cqw";
    } else if (word.length <= 7) {
      fontContainer.style.fontSize = "1.2cqw";
    } else if (word.length <= 9) {
      fontContainer.style.fontSize = "1px";
    }
    fontContainer.innerHTML = word;
    placeContainer.appendChild(fontContainer);
  });
  return placeContainer;
}

// Unused but preserved for consistency

function OpenDropDownForPlaces() {
  const dropdown = document.getElementById("place_id_for_drop_down_filter");
  if (dropdown) dropdown.classList.toggle("show");
}



