
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
function scrollFormDown(targetScroll) {
  const nextSection = document.getElementById(targetScroll);
  if (nextSection) {
    nextSection.scrollIntoView({ behavior: 'smooth' });
  }
}










      <div class="modal-container-main">
        {% if not user.is_authenticated %}
        <span class="button-close" onclick="closeViaje()" class="close">&times;</span>
        <div class="modal modal-sheet position-static d-block bg-body-secondary p-4 py-md-5" tabindex="-1" role="dialog" id="modalChoice">
          <div class="modal-dialog" role="document">
            <div class="modal-content rounded-3 shadow">
              <div class="modal-body p-4 text-center">
                <h5 class="mb-0">Please Login</h5>
                <p class="mb-0">Easy Sign up with our App</p>
              </div>
              <a href="{% url 'userProfile:registerUser' %}" style="text-decoration: none">
                <div class="modal-footer flex-nowrap p-0" style="min-height: 4em">
                  <button type="button" class="btn btn-lg btn-link fs-6 text-decoration-none col-6 m-0 rounded-0 border-end"><strong>Sign In</strong></button>
                  <button type="button" class="btn btn-lg btn-link fs-6 text-decoration-none col-6 m-0 rounded-0" data-bs-dismiss="modal"> Register</button>
                </div>
              </a>
            </div>
          </div>
        </div>
        {% endif %}
      {% if user.is_authenticated %}
        <div class="modal-container-sub modal-content rounded-4 shadow" style="background-color: whitesmoke;">
          <span class="button-close" onclick="closeViaje()" class="close">&times;</span>
            <div class="modal-item-head">
              <div class="flexBox-for-SVG" style="margin-top: 50px">
                <div class="first-section-form" ">
                  <span>
                    <div class="flexBox-option1"><input onchange="MakeOrFindSchedule('find')" required value="Find" checked type="radio" name="MakerOrLooker" id="imFind" /><label for="imFind">Look</label></div>
                    or
                    <div class="flexBox-option1"><input onchange="MakeOrFindSchedule('make')" required value="Make" type="radio" name="MakerOrLooker" id="imMake" /><label for="imMake">Create</label></div>
                    <span class="flexBox-for-Title">Schedule</span>
                    <div>
                    </div>
                  </span>
                 </div> 
              </div>
            </div>
          
          <div id="second-section-form" class="second-section-form" >
            <div style="text-align: center; display: block; color: #929090"><small>for</small></div>
            <div class="custom-field-item" style="text-align: center; margin: 15px">
              <select class="form-select" name="scheduleTravelType" onchange="schedule_Additional_Input(value)">
                <option selected="selected" value="RIDE">Car Pool</option>
                <optgroup label="Tour Types">
                  <option onclick="console.log(value)">BIKE</option>
                  <option onclick="console.log(value)">HIKE</option>
                  <option onclick="console.log(value)">DIVE</option>
                  <option onclick="console.log(value)">CAMP</option>
                </optgroup>
              </select>
              <div class="custom-field-item">
                <input name="meetPlace" required class="custom-field" placeholder="From:" />
                <div style="text-align: center;">to</div>
                <div class="custom-field-item">
                  {% if message %}
                  <input maxlength="32" name="place" required class="custom-field" placeholder="To: " list="destinationSearch" value="{{message}}" />
                  {% else %}
                  <input maxlength="32" name="place" required class="custom-field" placeholder="To: " list="destinationSearch" value="{{place.placename}}" />
                  {% endif %}
                </div>
              </div>
            </div>
            <div class="custom-field-item">
            </div>
          </div>
          <div class="modal-item-body">
            <div class="custom-field-container">
              <div id="third-section-form" >
                <div class="custom-field-item container-meetDate">
                  <label style="color: #a6a6a6">Date:</label>
                  <div class="flexBox-for-SVG">
                    <svg viewBox="0 0 24 24" class="user-svg-top">
                      <path d="M21.5 3h-2.75a.25.25 0 01-.25-.25V1a1 1 0 00-2 0v4.75a.75.75 0 01-.75.75.75.75 0 01-.75-.75V3.5a.5.5 0 00-.5-.5H8.25A.25.25 0 018 2.751V1a1 1 0 10-2 0v4.75a.75.75 0 01-.75.75.75.75 0 01-.75-.75V3.5A.5.5 0 004 3H2.5a2 2 0 00-2 2v17a2 2 0 002 2h19a2 2 0 002-2V5a2 2 0 00-2-2zM21 22H3a.5.5 0 01-.5-.5v-12A.5.5 0 013 9h18a.5.5 0 01.5.5v12a.5.5 0 01-.5.5z"></path>
                    </svg>

                    <input name="meetDate" required type="date" />
                    <span class="button-single button-add" onclick="addMoreDates()">+</span>
                  </div>
                </div>
                <div class="custom-field-item">
                  Contact:<br>
                  <input required type="text" name="detailsContact" class="custom-field" placeholder="Contact Details" value="{{request.user.email}}" />
                </div>
                <div class="custom-field-item">
                  <input name="scheduleCost" class="custom-field" placeholder="Budge: (optional)" style="font-size: 1rem" />
                </div>
              </div>
              <div class="custom-field-item">
                <textarea class="textarea-otherDetails" name="theDetails" required placeholder="looking for ...."></textarea>
              </div>
              <div style="text-align: center; padding-top: 10px; padding-bottom: 20px">
                <button onclick="alert('Please Wait for page to load')" class="btn btn-primary" type="submit" style="border-radius: 8px">Submit</button>
              </div>

            </div>

            <div class="additionalInputContainer"></div>
            <div class="additionalItineraryContainer"></div>
            <div>
              <div style="padding-bottom: 50px; padding-top: 15px">
                <div style="text-align: center; padding-left: 50px; padding-right: 50px">
                  <div style="padding: 14px" class="flexBox-for-SVG">
                    <svg viewBox="0 0 16 16" id="globe" style="padding-right: 8px">
                      <path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8zm7.5-6.923c-.67.204-1.335.82-1.887 1.855A7.97 7.97 0 0 0 5.145 4H7.5V1.077zM4.09 4a9.267 9.267 0 0 1 .64-1.539 6.7 6.7 0 0 1 .597-.933A7.025 7.025 0 0 0 2.255 4H4.09zm-.582 3.5c.03-.877.138-1.718.312-2.5H1.674a6.958 6.958 0 0 0-.656 2.5h2.49zM4.847 5a12.5 12.5 0 0 0-.338 2.5H7.5V5H4.847zM8.5 5v2.5h2.99a12.495 12.495 0 0 0-.337-2.5H8.5zM4.51 8.5a12.5 12.5 0 0 0 .337 2.5H7.5V8.5H4.51zm3.99 0V11h2.653c.187-.765.306-1.608.338-2.5H8.5zM5.145 12c.138.386.295.744.468 1.068.552 1.035 1.218 1.65 1.887 1.855V12H5.145zm.182 2.472a6.696 6.696 0 0 1-.597-.933A9.268 9.268 0 0 1 4.09 12H2.255a7.024 7.024 0 0 0 3.072 2.472zM3.82 11a13.652 13.652 0 0 1-.312-2.5h-2.49c.062.89.291 1.733.656 2.5H3.82zm6.853 3.472A7.024 7.024 0 0 0 13.745 12H11.91a9.27 9.27 0 0 1-.64 1.539 6.688 6.688 0 0 1-.597.933zM8.5 12v2.923c.67-.204 1.335-.82 1.887-1.855.173-.324.33-.682.468-1.068H8.5zm3.68-1h2.146c.365-.767.594-1.61.656-2.5h-2.49a13.65 13.65 0 0 1-.312 2.5zm2.802-3.5a6.959 6.959 0 0 0-.656-2.5H12.18c.174.782.282 1.623.312 2.5h2.49zM11.27 2.461c.247.464.462.98.64 1.539h1.835a7.024 7.024 0 0 0-3.072-2.472c.218.284.418.598.597.933zM10.855 4a7.966 7.966 0 0 0-.468-1.068C9.835 1.897 9.17 1.282 8.5 1.077V4h2.355z"></path>
                    </svg>
                    <input class="input-website" name="scheduleWebsite" type="link" placeholder="https://yourwebsite.com" />
                  </div>
                  <small class="small-item1">
                    No Website? <button onclick="alert('text us +640 231 231 or visit https.website.com')">Contact</button>
                    Us for a Website!
                  </small>
                </div>
                <div style="padding: 20px">
                  <div class="div-instagramContainer">
                    <input
                      class="input-website"
                      type="text"
                      placeholder=" Instagram Username"
                      name="
                    Username"
                    />
                    <svg class="u-svg-content" viewBox="0 0 112 112" x="0" y="0" id="svg-42cf">
                      <circle fill="rgb(182	25	147	)" cx="56.1" cy="56.1" r="55"></circle>
                      <path fill="#FFFFFF" d="M55.9,38.2c-9.9,0-17.9,8-17.9,17.9C38,66,46,74,55.9,74c9.9,0,17.9-8,17.9-17.9C73.8,46.2,65.8,38.2,55.9,38.2 z M55.9,66.4c-5.7,0-10.3-4.6-10.3-10.3c-0.1-5.7,4.6-10.3,10.3-10.3c5.7,0,10.3,4.6,10.3,10.3C66.2,61.8,61.6,66.4,55.9,66.4z"></path>
                      <path fill="#FFFFFF" d="M74.3,33.5c-2.3,0-4.2,1.9-4.2,4.2s1.9,4.2,4.2,4.2s4.2-1.9,4.2-4.2S76.6,33.5,74.3,33.5z"></path>
                      <path fill="#FFFFFF" d="M73.1,21.3H38.6c-9.7,0-17.5,7.9-17.5,17.5v34.5c0,9.7,7.9,17.6,17.5,17.6h34.5c9.7,0,17.5-7.9,17.5-17.5V38.8 C90.6,29.1,82.7,21.3,73.1,21.3z M83,73.3c0,5.5-4.5,9.9-9.9,9.9H38.6c-5.5,0-9.9-4.5-9.9-9.9V38.8c0-5.5,4.5-9.9,9.9-9.9h34.5 c5.5,0,9.9,4.5,9.9,9.9V73.3z"></path>
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      {% endif %}
      </div>