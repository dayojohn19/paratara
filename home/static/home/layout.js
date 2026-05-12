function createViaje(){(dom=document.querySelector(".modal-container-main")).style.display="block"}function closeViaje(){(dom=document.querySelector(".modal-container-main")).style.display="none"}function addMoreDates(){let e=document.createElement("div");e.classList.add("date-input-container");let a=document.createElement("span");a.classList.add("date-icon"),a.innerHTML=`
    <svg viewBox="0 0 24 24" class="calendar-icon">
      <path d="M21.5 3h-2.75a.25.25 0 01-.25-.25V1a1 1 0 00-2 0v4.75a.75.75 0 01-.75.75.75.75 0 01-.75-.75V3.5a.5.5 0 00-.5-.5H8.25A.25.25 0 018 2.751V1a1 1 0 10-2 0v4.75a.75.75 0 01-.75.75.75.75 0 01-.75-.75V3.5A.5.5 0 004 3H2.5a2 2 0 00-2 2v17a2 2 0 002 2h19a2 2 0 002-2V5a2 2 0 00-2-2zM21 22H3a.5.5 0 01-.5-.5v-12A.5.5 0 013 9h18a.5.5 0 01.5.5v12a.5.5 0 01-.5.5z"></path>
    </svg>
  `;let i=document.createElement("input");i.setAttribute("type","datetime-local"),i.setAttribute("name","meetDate"),i.classList.add("date-input"),i.required=!0;let l=document.createElement("span");l.classList.add("remove-date-btn"),l.innerHTML="–",l.onclick=()=>e.remove();let n=document.createElement("span");n.classList.add("add-date-btn"),n.innerHTML="+",n.onclick=addMoreDates,e.appendChild(a),e.appendChild(i),e.appendChild(l),e.appendChild(n),document.querySelector(".container-meetDate").appendChild(e)}function MakeOrFindSchedule(e){if(additionalItineraryContainer=document.querySelector("#additionalItineraryContainer"),"make"==e){(ItineraryContainer=document.createElement("div")).innerHTML=`
    <div class="custom-field-item">
        <textarea required class="TourOption-textarea textarea-otherDetails" name="additionalDetails"
            placeholder="Itinerary or other Information"></textarea>
    </div>
    `,additionalItineraryContainer.appendChild(ItineraryContainer);return}additionalItineraryContainer.innerHTML=""}function schedule_Additional_Input(e){let a=document.querySelector("#InputContainer");a.innerHTML="";let i=document.createElement("div");if("RIDE"===e){i.innerHTML=`
      <div id="div-RideContainer">
        <div class="radio-options-custom flexBox-for-SVG">
          <span class="flexBox-for-Title">I'm</span>
          <span>
            <div class="flexBox-option1">
              <input value="Driver" name="scheduleTypeAndMode" type="radio" id="Driver">
              <label for="Driver">Driver</label>
            </div> 
            <div class="flexBox-option1">
              <input value="Passenger" name="scheduleTypeAndMode" type="radio" id="Passenger">
              <label for="Passenger">Passenger</label>
            </div>
          </span>
        </div>

      </div>
    `,a.appendChild(i);return}"DIVE"===e&&(i.innerHTML=`
      <div id="div-DiveContainer">
        <div class="radio-options-custom flexBox-for-SVG">
          <span class="flexBox-for-Title"> <!-- INSERT DIVE SVG HERE --> </span>
          <div class="flexBox-for-SVG" style="flex-wrap: wrap;">
            <span class="flexBox-option1">
              <input value="Scuba Dive" name="scheduleTypeAndMode" type="radio" id="Scuba Dive">
              <label for="Scuba Dive">Scuba Dive</label>
            </span>
            <span class="flexBox-option1">
              <input id="Free Dive" value="Free Dive" name="scheduleTypeAndMode" type="radio">
              <label for="Free Dive">Free Dive</label>
            </span>
            <span class="flexBox-option1">
              <input id="Scuba and Free Dive" value="Scuba and Free Dive" name="scheduleTypeAndMode" type="radio">
              <label for="Scuba and Free Dive">Scuba and Free Dive</label>
            </span>
          </div>
        </div>
      </div>
    `),"HIKE"===e&&(i.innerHTML=`
      <div class="div-HikeContainer">
        <div class="flexBox-for-SVG" style="flex-wrap: wrap;">
          <span class="flexBox-option1">
            <input id="Chill Hike" name="scheduleTypeAndMode" type="radio" value="Chill Hike">
            <label for="Chill Hike"> Chill Hike </label>
          </span>
          <span class="flexBox-option1">
            <input id="Beginner Hike" name="scheduleTypeAndMode" type="radio" value="Beginner Hike">
            <label for="Beginner Hike">Beginner Hike</label>
          </span>
          <span class="flexBox-option1">
            <input id="Hard Hike" name="scheduleTypeAndMode" type="radio" value="Hard Hike">
            <label for="Hard Hike">Hard Hike</label>
          </span>
          <span class="flexBox-option1">
            <input name="scheduleTypeAndMode" type="radio" id="Camp Hike" value="Camp Hike">
            <label for="Camp Hike">Camp Hike</label>
          </span>
        </div>
      </div>
    `),"BIKE"===e&&(i.innerHTML=`
      <div class="div-BikeContainer">
        <div class="flexBox-for-SVG" style="flex-wrap: wrap;">
          <span class="flexBox-option1">
            <input type="radio" name="scheduleTypeAndMode" value="Chill Bike" id="Chill Bike">
            <label for="Chill Bike">Chill Bike</label>
          </span>
          <span class="flexBox-option1">
            <input type="radio" name="scheduleTypeAndMode" value="Hard Bike" id="Hard Bike">
            <label for="Hard Bike">Hard Bike</label>
          </span>
          <span class="flexBox-option1">
            <input type="radio" name="scheduleTypeAndMode" value="Long Bike" id="Long Bike">
            <label for="Long Bike">Long Bike</label>
          </span>
          <span class="flexBox-option1">
            <input type="radio" name="scheduleTypeAndMode" value="Camp Bike" id="Camp Bike">
            <label for="Camp Bike">Camp Bike</label>
          </span>
        </div>
      </div>
    `),"CAMP"===e&&(i.innerHTML=`
      <div class="div-CampContainer">
        <div class="flexBox-for-SVG" style="flex-wrap: wrap;">
          <span class="flexBox-option1">
            <input type="radio" name="scheduleTypeAndMode" value="Individual Camp" id="Individual Camp">
            <label for="Individual Camp">Individual Camp</label>
          </span>
          <span class="flexBox-option1">
            <input type="radio" name="scheduleTypeAndMode" value="Group Camp" id="Group Camp">
            <label for="Group Camp">Group Camp</label>
          </span>
          <span class="flexBox-option1">
            <input type="radio" name="scheduleTypeAndMode" value="Event Camp" id="Event Camp">
            <label for="Event Camp">Event Camp</label>
          </span>
        </div>
      </div>
    `),a.appendChild(i)}