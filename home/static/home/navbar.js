

function closeThisModal(ofWhat) {
  try {
    selfElement = event.srcElement;
    parentElement = selfElement.parentNode.parentNode.parentNode;
    parentElement.style.display = "none";
    return;
  } catch {}
  target = document.querySelector(`.${ofWhat}`);
  target.style.display = "none";
}
function deleteDates() {
  selfElement = event.srcElement;
  parentElement = selfElement.parentNode;
  console.log(parentElement);
  parentElement.remove();
}


function addRideInputs() {
  const optionContainer = document.createElement("div");
  optionContainer.setAttribute("id", "div-RideContainer");

  const radioWrapper = document.createElement("div");
  radioWrapper.className = "radio-options-custom flexBox-for-SVG";

  const spanTitle = document.createElement("span");
  spanTitle.className = "flexBox-for-Title";
  spanTitle.textContent = "I'm";

  const spanOptions = document.createElement("span");

  const driverDiv = document.createElement("div");
  driverDiv.className = "flexBox-option1";
  driverDiv.innerHTML = `
      <input value="Driver" name="scheduleTypeAndMode" type="radio" id="Driver">
      <label for="Driver">Driver</label>
  `;

  const passengerDiv = document.createElement("div");
  passengerDiv.className = "flexBox-option1";
  passengerDiv.innerHTML = `
      <input value="Passenger" name="scheduleTypeAndMode" type="radio" id="Passenger">
      <label for="Passenger">Passenger</label>
  `;

  spanOptions.appendChild(driverDiv);
  spanOptions.appendChild(passengerDiv);

  radioWrapper.appendChild(spanTitle);
  radioWrapper.appendChild(spanOptions);

  optionContainer.appendChild(radioWrapper);
  return optionContainer;
}


















