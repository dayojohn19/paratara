console.log("Navbar JS Loaded");
function newTabPlaceSearch(placename) {
  console.log("Place it Name: ", placename);
  x = prompt("", `Check ${placename}`);
  if (x == `Check ${placename}`) {
    window.open(`/place/${placename}`, "_blank");
  }
}
function openInNewTab(place, placeID) {
  openURL = `/place/${place}`;
  x = prompt("", `Check ${place}`);
  if (x == `Check ${place}`) {
    window.open(openURL, "_blank");
  }
}

function ChangeSearchInputValue(newInputValue) {
  document.querySelector(".where-to-go").value = newInputValue;
}

function OpenDropDownForPlaces() {
  document.getElementById("place_id_for_drop_down_filter").classList.toggle("show");
}

function FilterPlacesEachType() {
  console.log('Filtering..')
  setTimeout(() => {
    var input, filter, ul, li, a, i;
    input = document.getElementById("place_input_id_for_filter");
    filter = input.value.toUpperCase();
    div = document.getElementById("place_id_for_drop_down_filter");
    a = div.getElementsByClassName("search-drop-down");
    for (i = 0; i < a.length; i++) {
      txtValue = a[i].textContent || a[i].innerText;
      if (txtValue.toUpperCase().indexOf(filter) > -1) {
        a[i].style.display = "";
      } else {
        a[i].style.display = "none";
      }
    }
  }, 500);
}

function SlowAddToPage(i) {
  setTimeout(function () {
    bodyContainerList.appendChild(new CreateObjectOnLandingPageOfCarpool(i));
  }, 1);
}

function AddToSearchBox(ListToAddInSearchBox) {
  function getRand(){
    min = Math.ceil(0)
    max = Math.floor(PlaceDataList.length)
    return Math.floor(Math.random() * (max-min) + min);
  }
  setTimeout(() => {
    PlaceDataList = ListToAddInSearchBox["PlacesList"];
    seachBoxLists = document.querySelector("#place_id_for_drop_down_filter");

    try {
      bodyContainerList = document.querySelector(".container-list");
      if (bodyContainerList != null) {
        for (i = 0; i <= 20; i++) {

          SlowAddToPage(PlaceDataList[getRand()]);
        }
        // Create ADS HERE IF IN INDEX HTML
      }
    } catch (err) {
      console.log(err);
      console.log("\nThis is error");
    }

    for (i in PlaceDataList) {
      // newSearchItem = `<a class="dropdown-item search-drop-down" onclick="newTabPlaceSearch('ChangeSearchInputValue('${PlaceDataList[i].placename}')${PlaceDataList[i].placename}');" href="#about">${PlaceDataList[i].placename}</a>`;
      // newSearchItem = `<a class="dropdown-item search-drop-down" onclick="newTabPlaceSearch('${PlaceDataList[i].placename}');" href="#about">${PlaceDataList[i].placename}</a>`;
      newSearchItem = `<a class="dropdown-item search-drop-down" onclick="newTabPlaceSearch('${PlaceDataList[i].placename}');"">${PlaceDataList[i].placename}</a>`;
      // newSearchItem = `<a class="dropdown-item search-drop-down" onclick="console.log('${PlaceDataList[i].placename}');" href="#about">${PlaceDataList[i].placename}</a>`;
      seachBoxLists.innerHTML += newSearchItem;
    }
  }, 500);
}

function getCarpoolJSON() {
  fetch(window.location.origin + "/getcarpooljson/", {
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    // MAKE WHILE LOADING / FETCHING
  })
    .then((response) => response.json())
    .then((data) => {
      AddToSearchBox(data);
    });
}
// Not Used Now
function makePlacesFontSize(whatPlace, itsWidth) {
  placeContainer = document.createElement("div");
  whatPlace = whatPlace.split(" ");
  for (i in whatPlace) {
    fontContainer = document.createElement("div");
    if (whatPlace[i].length >= 6) {
      // BIGGER FONT SIzE
      fontContainer.style.fontSize = `1.7cqw`;
    } else if (whatPlace[i].length <= 7) {
      fontContainer.style.fontSize = "1.2cqw";
    } else if (whatPlace[i].length <= 9) {
      fontContainer.style.fontSize = "1px";
    }
    fontContainer.innerHTML = whatPlace[i];
    placeContainer.appendChild(fontContainer);
  }
  return placeContainer;
}

class CreateObjectOnLandingPageOfCarpool {
  constructor(PlaceItemToCreateObject) {
    // console.log(PlaceItemToCreateObject);
    // this.randomNumb = Math.floor(Math.random() * (300 - 1 + 1)) + 1;
    // var reviewCount, this.randomNumb, PlaceItemToCreateObject.placeID, PlaceItemToCreateObject.placename;

    // var PlaceItemToCreateObject.placeID, PlaceItemToCreateObject.placename;

    // var PlaceItemToCreateObject.SchedListCount;

    this.objectMainContainer = document.createElement("div");
    // reviews are Hidden
    // this.objectMainContainer.setAttribute("data-episode", `${PlaceItemToCreateObject.reviewCount} reviews`);
    this.objectMainContainer.setAttribute("class", "container-item");
    this.objectMainContainer.style.cssText = `
  width: 200px;
  height: 100px;
  background-color: lightblue;
  font-family: 'Montserrat', sans-serif !important; 
`;
    this.objectMainContainer.style.backgroundImage = `url(https://picsum.photos/id/${PlaceItemToCreateObject.id}/300/300)`;
    this.objectMainContainer.setAttribute("onclick", `openInNewTab('${PlaceItemToCreateObject.placename}','${PlaceItemToCreateObject.placeID}')`);

    this.objectSubContainer = document.createElement("div");
    this.objectSubContainer.setAttribute("class", `container-title translateCenter item-${PlaceItemToCreateObject.placeID}`);
    // this.objectSubContainer.appendChild(makePlacesFontSize(`${PlaceItemToCreateObject.placename}`, this.objectSubContainer.offsetWidth));
    // this.objectSubContainer.innerHTML = `<p class="h5 p-3">${PlaceItemToCreateObject.placename}</p>`;
    this.objectSubContainer.innerHTML = `<p class="h5 ">${PlaceItemToCreateObject.placename}</p>`;

    // this.objectSubItem = document.createElement("span");
    // this.objectSubItem.setAttribute("class", "container-count ride");
    // this.objectSubItem.value = `${PlaceItemToCreateObject.SchedListCount}`;

    this.objectMainContainer.appendChild(this.objectSubContainer);
    // this.objectMainContainer.appendChild(this.objectSubItem);
    return this.objectMainContainer;
  }

  // ele.style.backgroundImage = `url(https://picsum.photos/id/${this.randomNumb}/300/300)`;
}

document.addEventListener("DOMContentLoaded", (event) => {
  getCarpoolJSON();
  seachBoxLists = document.querySelector("#place_id_for_drop_down_filter");
});
