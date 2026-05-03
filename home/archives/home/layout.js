// **************************************************
// ************** for LOG IN JS FETCH ***************
// **************************************************
function loginUserJSONForm() {
  if (document.querySelector(".container-login").style.display == "block") {
    document.querySelector(".container-login").style.display = "none";
  } else {
    document.querySelector(".container-login").style.display = "block";
  }
}

// **************************************************
// ************** endfor LOG IN JS FETCH ***************
// **************************************************

// For Additional Inputs on Schedule Type
function schedule_Additional_Input(what_Type) {
  InputContainer = document.querySelector(".additionalInputContainer");
  InputContainer.innerHTML = "";
  OptionContainer = document.createElement("div");

  if (what_Type == "RIDE") {
    OptionContainer.innerHTML = `
                        <div id="div-RideContainer">
                            <div class="radio-options-custom flexBox-for-SVG">
                                <span class="flexBox-for-Title">I'm</span>
                                <span>
                                    <div class="flexBox-option1">
                                        <input value="Driver" name="scheduleTypeAndMode" type="radio" id="Driver">
                                        <label for="Driver">Driver</label>
                                    </div>
                                    <div class="flexBox-option1">
                                        <input value="Passenger" name="scheduleTypeAndMode" type="radio"
                                            id="Passenger"><label for="Passenger">Passenger</label>
                                    </div>
                                </span>
                            </div>
                            <div class="flexBox-for-SVG">Meet
                                <input type="time">
                                <span>
                                    <svg viewBox="0 0 24 24" class="user-svg-top">
                                        <path
                                            d="M12 0a12 12 0 1012 12A12.013 12.013 0 0012 0zm5.2 17.221a1.016 1.016 0 01-1.413.062l-4.959-4.546A1 1 0 0110.5 12V6.5a1 1 0 012 0v5.06l4.634 4.248a1 1 0 01.066 1.414z">
                                        </path>
                                    </svg>
                                </span>
                            </div>
                        </div>            
            
            `;
    // END RETURN SINCE IT IS JUST A RIDE
    InputContainer.appendChild(OptionContainer);
    return;
  }
  if (what_Type == "DIVE") {
    OptionContainer.innerHTML = `
                        <div id="div-DiveContainer">
                            <div class="radio-options-custom flexBox-for-SVG">
                                <span class="flexBox-for-Title">
                                    <!-- INSERT DIVE SVG HERE -->
                                </span>
                                <div class="flexBox-for-SVG" style="flex-wrap: wrap;">
                                    <span class="flexBox-option1">
                                        <input value="Scuba Dive" name="scheduleTypeAndMode" type="radio"
                                            id="Scuba Dive"><label for="Scuba Dive">Scuba
                                            Dive</label>
                                    </span>
                                    <span class="flexBox-option1">
                                        <input id="Free Dive" value="Free Dive" name="scheduleTypeAndMode"
                                            type="radio"><label for="Free Dive">Free
                                            Dive</label>
                                    </span>
                                    <span class="flexBox-option1">
                                        <input id="Scuba and Free Dive" value="Scuba and Free Dive"
                                            name="scheduleTypeAndMode" type="radio"><label
                                            for="Scuba and Free Dive">Scuba
                                            and Free Dive</label>
                                    </span>
                                </div>
                            </div>
                        </div>            
            `;
  }
  if (what_Type == "HIKE") {
    OptionContainer.innerHTML = `
                        <div class="div-HikeContainer">
                            <div class="flexBox-for-SVG" style="flex-wrap: wrap;">
                                <span class="flexBox-option1"><input id="Chill Hike" name="scheduleTypeAndMode"
                                        type="radio" value="Chill Hike"><label for="Chill Hike">
                                        Chill Hike
                                    </label>
                                </span>
                                <span class="flexBox-option1"><input id="Beginner Hike" name="scheduleTypeAndMode"
                                        type="radio" value="Beginner Hike"><label for="Beginner Hike">Beginner
                                        Hike</label>
                                </span>
                                <span class="flexBox-option1"><input id="Hard Hike" name="scheduleTypeAndMode"
                                        type="radio" value="Hard Hike"><label for="Hard Hike">Hard Hike</label>
                                </span>
                                <span class="flexBox-option1"><input name="scheduleTypeAndMode" type="radio"
                                        id="Camp Hike" value="Camp Hike"><label for="Camp Hike">Camp Hike</label>
                                </span>
                            </div>
                        </div>            
            
            `;
  }
  if (what_Type == "BIKE") {
    OptionContainer.innerHTML = `
                        <div class="div-BikeContainer">
                            <div class="flexBox-for-SVG" style="flex-wrap: wrap;">
                                <span class="flexBox-option1">
                                    <input type="radio" name="scheduleTypeAndMode" value="Chill Bike"
                                        id="Chill Bike"><label for="Chill Bike">Chill
                                        Bike</label>
                                </span>
                                <span class="flexBox-option1">
                                    <input type="radio" name="scheduleTypeAndMode" value="Hard Bike"
                                        id="Hard Bike"><label for="Hard Bike">Hard
                                        Bike</label>
                                </span>
                                <span class="flexBox-option1">
                                    <input type="radio" name="scheduleTypeAndMode" value="Long Bike"
                                        id="Long Bike"><label for="Long Bike">Long
                                        Bike</label>
                                </span>

                                <span class="flexBox-option1">
                                    <input type="radio" name="scheduleTypeAndMode" value="Camp Bike"
                                        id="Camp Bike"><label for="Camp Bike">Camp
                                        Bike</label>
                                </span>
                            </div>
                        </div>            
            `;
  }
  if (what_Type == "CAMP") {
    OptionContainer.innerHTML = `
                     <div class="div-CampContainer">
                            <div class="flexBox-for-SVG" style="flex-wrap: wrap;">
                                <span class="flexBox-option1">
                                    <input type="radio" name="scheduleTypeAndMode" value="Individual Camp"
                                        id="Individual Camp"><label for="Individual Camp">Individual Camp</label>
                                </span>
                                <span class="flexBox-option1">
                                    <input type="radio" name="scheduleTypeAndMode" value="Group Camp"
                                        id="Group Camp"><label for="Group Camp">Group Camp</label>
                                </span>
                                <span class="flexBox-option1">
                                    <input type="radio" name="scheduleTypeAndMode" value="Event Camp"
                                        id="Event Camp"><label for="Event Camp">Event Camp</label>
                                </span>
                            </div>
                        </div>            
            `;
  }

  InputContainer.appendChild(OptionContainer);
  return;
}
function MakeOrFindSchedule(makeOfind) {
  additionalItineraryContainer = document.querySelector(".additionalItineraryContainer");
  if (makeOfind == "make") {
    ItineraryContainer = document.createElement("div");
    ItineraryContainer.innerHTML = `
    <div class="custom-field-item">
        <textarea class="TourOption-textarea textarea-otherDetails" name="additionalDetails"
            placeholder="Itinerary or other Information"></textarea>
    </div>
    `;
    additionalItineraryContainer.appendChild(ItineraryContainer);
    return;
  }
  additionalItineraryContainer.innerHTML = "";
}

function deleteDates() {
  selfElement = event.srcElement;
  parentElement = selfElement.parentNode;
  console.log(parentElement);
  parentElement.remove();
}
function addMoreDates() {
  // Button to delete CAlendar
  dateContainer = document.createElement("div");
  dateContainer.setAttribute("class", "flexBox-for-SVG dateContainerDiv");
  dateCalendarIcon = document.createElement("span");
  dateCalendarIcon.innerHTML = `
    <svg viewBox="0 0 24 24" class="user-svg-top" >
        <path
            d="M21.5 3h-2.75a.25.25 0 01-.25-.25V1a1 1 0 00-2 0v4.75a.75.75 0 01-.75.75.75.75 0 01-.75-.75V3.5a.5.5 0 00-.5-.5H8.25A.25.25 0 018 2.751V1a1 1 0 10-2 0v4.75a.75.75 0 01-.75.75.75.75 0 01-.75-.75V3.5A.5.5 0 004 3H2.5a2 2 0 00-2 2v17a2 2 0 002 2h19a2 2 0 002-2V5a2 2 0 00-2-2zM21 22H3a.5.5 0 01-.5-.5v-12A.5.5 0 013 9h18a.5.5 0 01.5.5v12a.5.5 0 01-.5.5z">
        </path>
    </svg>`;
  // HERE PUT CALENDAR
  dateElement = document.createElement("input");
  dateElement.setAttribute("type", "date");
  dateElement.setAttribute("name", "meetDate");
  dateRemoveButton = document.createElement("span");
  dateRemoveButton.setAttribute("onclick", "deleteDates()");
  dateRemoveButton.innerHTML = "-";
  dateRemoveButton.setAttribute("class", "button-single button-remove");
  dateAddButton = document.createElement("span");
  dateAddButton.setAttribute("onclick", "addMoreDates()");
  dateAddButton.setAttribute("class", "button-single button-add");
  dateAddButton.innerHTML = "+";
  
  dateContainer.appendChild(dateCalendarIcon);
  dateContainer.appendChild(dateElement);
  dateContainer.appendChild(dateRemoveButton);
  dateContainer.appendChild(dateAddButton);
  // dateHR = document.createElement("br");
  // document.querySelector(".container-meetDate").appendChild(dateHR);
  document.querySelector(".container-meetDate").appendChild(dateContainer);
}

function createViaje() {
  dom = document.querySelector(".modal-container-main");
  dom.style.display = "block";
}

function closeViaje() {
  dom = document.querySelector(".modal-container-main");
  dom.style.display = "none";
}

// --------- SEND FEEDBACK ---------
function sendEmail() {
  feedbackMessage = prompt("Your Feed Back: ", "");
  Email.send({
    Host: "smtp.elasticemail.com",
    Username: "repapaka20@gmail.com",
    Password: "20B28409FAB2EC360F970DEBC62ACB854E4B",
    To: "dayo_john16@yahoo.com",
    From: "repapaka20@gmail.com",
    Subject: "Viaje Feed Back",
    Body: `${feedbackMessage}`,
  }).then((message) => alert("Please Check You Spam Layout JS", message, "to ensure receiving your message please email us Twice"));
}
// -------- END SEND FEED BACK --------

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
