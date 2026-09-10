


function OpentheModal(ofWhat) {
    x = document.querySelector(`.${ofWhat}`)
    x.style.display = 'block'
}

// -----------------------------------------------------------
// schedDates = []
allDates = [];
allTD = document.querySelectorAll('.wed,.mon,.tue,.thu,.fri,.sat,.sun');
allTD.forEach(element => {
    if (element.innerHTML != '&nbsp') {
        allDates.push(element)
    }
});

// -----------------------------------------------------------
// ------------- FOR CALENDAR AND OBJECTS -------------------------


// ********
// ALL CALENDAR
schedDatas = []
allobjectList = []
function dateObjects(dataD) {
    this.createObject = (dateD) => {
        if (dataD.additionalDetails) {
            schedDatas.push(dataD)
        }
        try {
            istTher = document.querySelector(`#eventCount-${dataD.dateN}`)
            istTher.innerHTML = parseInt(istTher.innerHTML) + 1
            for (n in allobjectList) {
                if (allobjectList[n].dateID == dateD.dateN) {
                    allobjectList[n].DateObjectList.push(dataD)
                    break
                } else { console.log('Not Found') }
            }
            return
        }
        catch {
            this.dateID = dateD.dateN
            this.DateObjectList = [dataD]
            allobjectList.push(this)
            addEvent = document.createElement('div');
            addEvent.innerHTML = `
                       
                <span onclick="showObjectButton('${this.dateID
                }')" id="eventCount-${dataD.dateN}"  class="badge">1</span>`
            allDates[dataD.dateN + 6].appendChild(addEvent)
            return
        }

    }
}
// SHOWING DISCUSSIONS 
function showDiscussions(){
    calendarObjectList_Container = document.querySelector("#calendar-objects-list");
    calendarObjectList_Container.innerHTML = '';
    // TODO HERE FECTCH MODELS
}
// SHOWING LIST OF SCHEDULE AND EVENT IN DATE
function showObjectButton(objectOf) { // BUTTON WHEN CLICKED ON THE CALENDAR
    calendarObjectList_Container = document.querySelector("#calendar-objects-list");
    calendarObjectList_Container.innerHTML = '';
    showObjectListDIv(objectOf)
}
function showObjectListDIv(objectOf) {
    calendarObjectList_Container = document.querySelector("#calendar-objects-list");
    calendarObjectList_Container.innerHTML = '';
    if (objectOf == undefined) {
        console.log('Print everything', allobjectList)
        calendarObjectList_Container = document.querySelector("#calendar-objects-list");
        for (i in allobjectList) {
            makeTheDivNow(allobjectList[i].DateObjectList)
        }
    } else {
        for (i in allobjectList) {
            if (allobjectList[i].dateID == objectOf) {
                makeTheDivNow(allobjectList[i].DateObjectList)
            }
        }
    }
}
function isThereMeetTime(meetTime) {
    if (meetTime != null) {
        thereIs = `
                <svg viewBox="0 0 24 24" class="user-svg-top" style="padding-right:1px">
                    <path
                        d="M12 0a12 12 0 1012 12A12.013 12.013 0 0012 0zm5.2 17.221a1.016 1.016 0 01-1.413.062l-4.959-4.546A1 1 0 0110.5 12V6.5a1 1 0 012 0v5.06l4.634 4.248a1 1 0 01.066 1.414z">
                    </path>
                </svg>${meetTime}
            `
        return thereIs
    }
    return ''
}
function whatScheduleType(itsType) {
    // ON SVG INPUT CLASS  class="user-svg-top"
    if (itsType == 'RIDE') {
        return rideSVG = `<svg viewBox="0 0 20 20" class="user-svg-top svg-car"><path clip-rule="evenodd" d="M18.478 8.182a.21.21 0 00.057.174 3.71 3.71 0 011.048 2.581v1.667a2.078 2.078 0 01-1.326 1.93.21.21 0 00-.132.194v1.623a1.875 1.875 0 11-3.75 0v-1.459a.208.208 0 00-.208-.208H5.833a.208.208 0 00-.208.208v1.459a1.875 1.875 0 11-3.75 0v-1.626a.21.21 0 00-.133-.194A2.077 2.077 0 01.417 12.6v-1.667a3.71 3.71 0 011.045-2.577.207.207 0 00-.046-.325L.75 7.647A1.25 1.25 0 112 5.48l.886.512a.21.21 0 00.31-.146l.333-1.986a2.493 2.493 0 012.466-2.091h8.007a2.492 2.492 0 012.465 2.09l.334 1.985a.208.208 0 00.309.147l.887-.513a1.25 1.25 0 011.25 2.167l-.666.386a.207.207 0 00-.103.15zm-4.473-4.745h-8.01a.833.833 0 00-.822.695l-.399 2.394a.208.208 0 00.206.242h10.04a.208.208 0 00.206-.24l-.4-2.394a.833.833 0 00-.821-.697zm2.245 6.667a1.25 1.25 0 110 2.5 1.25 1.25 0 010-2.5zm-12.5 0a1.25 1.25 0 100 2.5 1.25 1.25 0 000-2.5z" fill-rule="evenodd"></path></svg>`
    }
    if (itsType == 'BIKE') {
        return bikeSVG = `<svg viewBox="0 0 16 16" class="user-svg-top "><path d="M4 4.5a.5.5 0 0 1 .5-.5H6a.5.5 0 0 1 0 1v.5h4.14l.386-1.158A.5.5 0 0 1 11 4h1a.5.5 0 0 1 0 1h-.64l-.311.935.807 1.29a3 3 0 1 1-.848.53l-.508-.812-2.076 3.322A.5.5 0 0 1 8 10.5H5.959a3 3 0 1 1-1.815-3.274L5 5.856V5h-.5a.5.5 0 0 1-.5-.5zm1.5 2.443-.508.814c.5.444.85 1.054.967 1.743h1.139L5.5 6.943zM8 9.057 9.598 6.5H6.402L8 9.057zM4.937 9.5a1.997 1.997 0 0 0-.487-.877l-.548.877h1.035zM3.603 8.092A2 2 0 1 0 4.937 10.5H3a.5.5 0 0 1-.424-.765l1.027-1.643zm7.947.53a2 2 0 1 0 .848-.53l1.026 1.643a.5.5 0 1 1-.848.53L11.55 8.623z" /></svg>`
    }
    if (itsType == 'HIKE') {
        return hikeSVG = `<svg viewBox="0 0 12.2 18.6" class="user-svg-top"><path d="M7.5 7.3c-.3.7-.7 1.3-1 2 .5.7 1.4 1.5 1.9 2.2.6.8 1 1.7 1.1 2.8.1 1.3.2 2.3.3 3.5 0 .4-.4.8-.8.8s-1.1-.2-1.1-.6c-.3-1.4-.5-2.8-.8-4.2-.1-.3-.2-.6-.4-.8-.8-.8-1.6-1.7-2.4-2.5-.7-.6-.8-1.2-.6-2 .1-.2.2-.5.3-.7.5-1 1.1-2 1.6-3 .2-.4.3-.5.5-.8.3-.3.6-.3 1-.2.3.1.4.2.6.4.4.2.7.4.8.8.3.8.4 1.2.8 1.9.1.3.7.7 1 .8.6.3.8.3 1.4.6.5.2.5.7.4 1.1s-.7.5-1 .4c-.8-.2-1.1-.3-1.8-.5-.2-.1-.9-.6-1-.8-.4-.4-.5-.7-.8-1.2zm-5.4 2.9h-.3c0-.5.1-.9.2-1.3-.2-.1-.3-.1-.4-.2-.3.5-.5 1-.8 1.5-.1-.1-.3-.1-.3-.2.2-.4.5-.9.8-1.3-.2-.1-.2-.1-.3-.1-.9-.4-1.1-.7-1-1.8.1-.9.6-1.6 1.1-2.4.1-.2.2-.3.3-.4.5-.9 1.4-1.3 2.4-1.4h.3c.4.2.9.4 1.4.6-1.8 2-2.9 4.3-3.4 7zm1.7.9c.5.5 1.1 1 1.6 1.6.1.1.1.2 0 .3-.2.7-.3 1.4-.6 2-.1.2-.4.8-.6 1-1 1-1.6 1.4-2.6 2.3-.3.3-1 .2-1.3-.1-.3-.3-.5-1-.1-1.4.7-.7 1.3-1.2 2.1-1.9.3-.3.5-.6.7-1 .4-.9.6-1.6.8-2.5v-.3zm3.3-9.3C7.1.8 7.9 0 9 0c1 0 1.9.9 1.8 1.9 0 1-.8 1.8-1.9 1.8s-1.8-.8-1.8-1.9z"></path></svg>`
    }
    // TO EDIT TO ITS REAL SVG
    if (itsType == 'CAMP') {
        return campSVG = `<svg class="user-svg-top" viewBox="0 0 16 16"><path d="M7 2.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0zm4.225 4.053a.5.5 0 0 0-.577.093l-3.71 4.71-2.66-2.772a.5.5 0 0 0-.63.062L.002 13v2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4.5l-4.777-3.947z"></path></svg>`
    }
    if (itsType == 'DIVE') {
        return diveSVG = `<svg class="user-svg-top" viewBox="0 0 16 16"><path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm6.43-5.228a7.025 7.025 0 0 1-3.658 3.658l-1.115-2.788a4.015 4.015 0 0 0 1.985-1.985l2.788 1.115zM5.228 14.43a7.025 7.025 0 0 1-3.658-3.658l2.788-1.115a4.015 4.015 0 0 0 1.985 1.985L5.228 14.43zm9.202-9.202-2.788 1.115a4.015 4.015 0 0 0-1.985-1.985l1.115-2.788a7.025 7.025 0 0 1 3.658 3.658zm-8.087-.87a4.015 4.015 0 0 0-1.985 1.985L1.57 5.228A7.025 7.025 0 0 1 5.228 1.57l1.115 2.788zM8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6z"></path></svg>`
    }
    return ''
}
function MakeOrFind(orwhat) {
    if (orwhat == 'Make') {
        return `
        <svg class="user-svg-top" viewBox="0 0 16 16">
            <path fill-rule="evenodd"
                d="M15.817.113A.5.5 0 0 1 16 .5v14a.5.5 0 0 1-.402.49l-5 1a.502.502 0 0 1-.196 0L5.5 15.01l-4.902.98A.5.5 0 0 1 0 15.5v-14a.5.5 0 0 1 .402-.49l5-1a.5.5 0 0 1 .196 0L10.5.99l4.902-.98a.5.5 0 0 1 .415.103zM10 1.91l-4-.8v12.98l4 .8V1.91zm1 12.98 4-.8V1.11l-4 .8v12.98zm-6-.8V1.11l-4 .8v12.98l4-.8z">
            </path>
        </svg>            
            `
    }
    if (orwhat == 'Find') {
        return `
        <svg class="user-svg-top" viewBox="0 0 16 16" >
            <path
                d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z">
            </path>
        </svg>            
            
            `
    }
    return ''
}
function hasInstagram(ig) {
    if (ig == '') {
        return ''
    }
    return ig = `
        <div style="display:flex; align-items:center;line-height: 1;">
            <span>
                <svg class="u-svg-content" viewBox="0 0 112 112" x="0" y="0" id="svg-42cf">
                    <circle fill="rgb(182	25	147	)" cx="56.1" cy="56.1" r="55"></circle>
                    <path fill="#FFFFFF"
                        d="M55.9,38.2c-9.9,0-17.9,8-17.9,17.9C38,66,46,74,55.9,74c9.9,0,17.9-8,17.9-17.9C73.8,46.2,65.8,38.2,55.9,38.2
                                        z M55.9,66.4c-5.7,0-10.3-4.6-10.3-10.3c-0.1-5.7,4.6-10.3,10.3-10.3c5.7,0,10.3,4.6,10.3,10.3C66.2,61.8,61.6,66.4,55.9,66.4z">
                    </path>
                    <path fill="#FFFFFF"
                        d="M74.3,33.5c-2.3,0-4.2,1.9-4.2,4.2s1.9,4.2,4.2,4.2s4.2-1.9,4.2-4.2S76.6,33.5,74.3,33.5z">
                    </path>
                    <path fill="#FFFFFF" d="M73.1,21.3H38.6c-9.7,0-17.5,7.9-17.5,17.5v34.5c0,9.7,7.9,17.6,17.5,17.6h34.5c9.7,0,17.5-7.9,17.5-17.5V38.8
                                        C90.6,29.1,82.7,21.3,73.1,21.3z M83,73.3c0,5.5-4.5,9.9-9.9,9.9H38.6c-5.5,0-9.9-4.5-9.9-9.9V38.8c0-5.5,4.5-9.9,9.9-9.9h34.5
                                        c5.5,0,9.9,4.5,9.9,9.9V73.3z"></path>
                </svg>
            </span>
            <span style="padding-left:5px">
                <a href="https://instagram/${ig}" style="text-decoration:none;">${plan.posterInstagram}</a>                                                            
            </span>
        </div>         
        `
}

function isThereWebsite(web) {

    if (web != "") {
        return thereIs = `
            <div  class="flexBox-for-SVG" style="justify-content: left;">
                                    <svg viewBox="0 0 16 16" id="globe" style="padding-right: 8px;">
                                        <path
                                            d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8zm7.5-6.923c-.67.204-1.335.82-1.887 1.855A7.97 7.97 0 0 0 5.145 4H7.5V1.077zM4.09 4a9.267 9.267 0 0 1 .64-1.539 6.7 6.7 0 0 1 .597-.933A7.025 7.025 0 0 0 2.255 4H4.09zm-.582 3.5c.03-.877.138-1.718.312-2.5H1.674a6.958 6.958 0 0 0-.656 2.5h2.49zM4.847 5a12.5 12.5 0 0 0-.338 2.5H7.5V5H4.847zM8.5 5v2.5h2.99a12.495 12.495 0 0 0-.337-2.5H8.5zM4.51 8.5a12.5 12.5 0 0 0 .337 2.5H7.5V8.5H4.51zm3.99 0V11h2.653c.187-.765.306-1.608.338-2.5H8.5zM5.145 12c.138.386.295.744.468 1.068.552 1.035 1.218 1.65 1.887 1.855V12H5.145zm.182 2.472a6.696 6.696 0 0 1-.597-.933A9.268 9.268 0 0 1 4.09 12H2.255a7.024 7.024 0 0 0 3.072 2.472zM3.82 11a13.652 13.652 0 0 1-.312-2.5h-2.49c.062.89.291 1.733.656 2.5H3.82zm6.853 3.472A7.024 7.024 0 0 0 13.745 12H11.91a9.27 9.27 0 0 1-.64 1.539 6.688 6.688 0 0 1-.597.933zM8.5 12v2.923c.67-.204 1.335-.82 1.887-1.855.173-.324.33-.682.468-1.068H8.5zm3.68-1h2.146c.365-.767.594-1.61.656-2.5h-2.49a13.65 13.65 0 0 1-.312 2.5zm2.802-3.5a6.959 6.959 0 0 0-.656-2.5H12.18c.174.782.282 1.623.312 2.5h2.49zM11.27 2.461c.247.464.462.98.64 1.539h1.835a7.024 7.024 0 0 0-3.072-2.472c.218.284.418.598.597.933zM10.855 4a7.966 7.966 0 0 0-.468-1.068C9.835 1.897 9.17 1.282 8.5 1.077V4h2.355z">
                                        </path>
                                    </svg>            
            <a href="${web}" target="_blank">${web}</a>
            </div>
            `
    }
    return ''

}
function viewAdditionalDetails(PlanID) {
    // #####
    // ### TODO FIND schedDatas that has scheduleID same as as PlanID and get its additional Details
    for (i in schedDatas) {
        if (schedDatas[i].scheduleID == PlanID) {
            console.log("WEBSITEL ", schedDatas[i].scheduleWebsite)
            console.log('THE ADDITIONAL DETAILS: ', schedDatas[i].additionalDetails)
            document.querySelector('.additionalDetailsModal').style.display = 'block'
            document.querySelector('#AdditionalDetailsContainer').innerHTML = schedDatas[i].additionalDetails.replace(/\r?\n/g, '<br />')
            if (schedDatas[i].scheduleWebsite != '') {
                document.querySelector("#AdditionalDetailsFooter").innerHTML = `<a href="${schedDatas[i].scheduleWebsite}">Visit Us</a>`
            }

            document.querySelector("#AdditionalDetailsHeader").innerHTML = `${schedDatas[i].scheduleTitle
                }`
            break
        }
    }
}

function viewAdditionalDetailsButton(details) {
    if (details.additionalDetails != "") {
        theDetails = details.additionalDetails
        return button = `
        <button class="button-moreInfo" id="${details.scheduleID}" onclick="viewAdditionalDetails(id)" >More Info</button>
            `
    }
    return ''

}

function makeTheDivNow(toBeMadeinDiv) {



    for (ii in toBeMadeinDiv) {
        calendarObject = document.createElement('div')
        plan = toBeMadeinDiv[ii]
        console.log('Plan: ', typeof (plan.timestamp), ii)
        // todo Copy from this
        calendarObjectList_Container.appendChild(calendarObject)
        // COPY UNTIL HERE THE DETAILS
        //  ************ FOR NEW SCHEDULE
        // ITEM CONTAINER
        calendarObject = document.createElement('div')
        calendarObject.setAttribute('class', 'item-1')
        insideObject_li = document.createElement('li')
        userBodyContainer = document.createElement('div')
        insideObject_li.setAttribute('class', 'collection-item')
        userBodyContainer.setAttribute('class', 'addPaddingLeft')
        userHeader = `
                <div style="display:flex; align-items:center">
                    <svg viewBox="0 0 24 24"  class="user-svg-top">
                        <path
                            d="M21.5 3h-2.75a.25.25 0 01-.25-.25V1a1 1 0 00-2 0v4.75a.75.75 0 01-.75.75.75.75 0 01-.75-.75V3.5a.5.5 0 00-.5-.5H8.25A.25.25 0 018 2.751V1a1 1 0 10-2 0v4.75a.75.75 0 01-.75.75.75.75 0 01-.75-.75V3.5A.5.5 0 004 3H2.5a2 2 0 00-2 2v17a2 2 0 002 2h19a2 2 0 002-2V5a2 2 0 00-2-2zM21 22H3a.5.5 0 01-.5-.5v-12A.5.5 0 013 9h18a.5.5 0 01.5.5v12a.5.5 0 01-.5.5z">
                        </path>
                    </svg>
                    <span class="badge">
                        <strong style="letter-spacing:1px;">${plan.monthN} / <strong style="font-size:larger">${plan.dateN}</strong> / ${plan.yearN} 
                        </strong>
                    </span>
                    
                    <small style="display:flex; align-items:center">
                        ${isThereMeetTime(plan.meetTime)}
                        ${whatScheduleType(plan.scheduleTravelType)}
                        ${MakeOrFind(plan.MakerOrLooker)}
                        

                    </small>
                </div>
        `
        userBodyContainer.innerHTML = `
                                <strong>${plan.scheduleTitle}</strong>
                                <details class="quote-details-container">
                                    <summary id="summary-${plan.scheduleID}" onclick="addReviewFromSchedulID(id)" class="summary-container">
                                        <div class="flexBox-for-SVG" style="justify-content: left;"> 
                                            <span>
                                                <svg class="" viewBox="0 0 16 16" id="geo-alt" >
                                                    <path
                                                        d="M12.166 8.94c-.524 1.062-1.234 2.12-1.96 3.07A31.493 31.493 0 0 1 8 14.58a31.481 31.481 0 0 1-2.206-2.57c-.726-.95-1.436-2.008-1.96-3.07C3.304 7.867 3 6.862 3 6a5 5 0 0 1 10 0c0 .862-.305 1.867-.834 2.94zM8 16s6-5.686 6-10A6 6 0 0 0 2 6c0 4.314 6 10 6 10z">
                                                    </path>
                                                    <path d="M8 8a2 2 0 1 1 0-4 2 2 0 0 1 0 4zm0 1a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"></path>
                                                </svg>
                                            </span>
                                            <span>                                        
                                                <strong>${plan.meetPlace} <small class="container-reviewCount">${plan.reviewCount} views</small></strong>
                                            </span>
                                        </div>
                                    </summary>
                                    <blockquote class="collection-item">
                                        <div class="quote-details-content">
                                            <div style="padding-left:auto;padding-right:0; ">
                                                <div class="user-author-container">
                                                            <button class="user-author-image" onclick="alert('ye')"></button>
                                                        
                                                            <div>
                                                                <div>
                                                                    <svg viewBox="0 0 16 16" class="user-svg" onclick="alert('User is Verified')">
                                                                        <path
                                                                            d="M10.067.87a2.89 2.89 0 0 0-4.134 0l-.622.638-.89-.011a2.89 2.89 0 0 0-2.924 2.924l.01.89-.636.622a2.89 2.89 0 0 0 0 4.134l.637.622-.011.89a2.89 2.89 0 0 0 2.924 2.924l.89-.01.622.636a2.89 2.89 0 0 0 4.134 0l.622-.637.89.011a2.89 2.89 0 0 0 2.924-2.924l-.01-.89.636-.622a2.89 2.89 0 0 0 0-4.134l-.637-.622.011-.89a2.89 2.89 0 0 0-2.924-2.924l-.89.01-.622-.636zm.287 5.984-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7 8.793l2.646-2.647a.5.5 0 0 1 .708.708z">
                                                                        </path>
                                                                    </svg>
                                                                    <span class="user-author"><small>${plan.posterName} </small> </span>
                                                                </div>
                                                                <div>
                                                                    <svg viewBox="0 0 24 24" class="user-svg">
                                                                        <path
                                                                            d="M12 0a12 12 0 1012 12A12.013 12.013 0 0012 0zm.25 5a1.5 1.5 0 11-1.5 1.5 1.5 1.5 0 011.5-1.5zm2.25 13.5h-4a1 1 0 010-2h.75a.25.25 0 00.25-.25v-4.5a.25.25 0 00-.25-.25h-.75a1 1 0 010-2h1a2 2 0 012 2v4.75a.25.25 0 00.25.25h.75a1 1 0 110 2z">
                                                                        </path>
                                                                    </svg>
                                                                    <span class="user-contactInformation" readonly  value="${plan.detailsContact}">${plan.detailsContact}</span>
                                                                </div>
                                                            </div>
                                                </div>                                            
                                            </div>                                            
                                            <div class="addPaddingLeft">
                                                "${plan.otherDetails.replace(/\r?\n/g, '<br />')}"
                                                <div style="margin-top:8px; margin-bottom:8px">
                                                    #${plan.scheduleTypeAndMode}
                                                    ${hasInstagram(plan.posterInstagram)}
                                                    ${isThereWebsite(plan.scheduleWebsite)}
                                                </div>
                                                
                                                <div>
                                                ${viewAdditionalDetailsButton(plan)}
                                                    <div  id="comments-${plan.scheduleID}">
                                                    </div>
                                                    <button onclick="CommentBuilder(${plan.scheduleID})"> ${plan.comment.length} Comments</button>
                                                    <div>
                                                    <input id="input-${plan.scheduleID}"  placeholder="comment" type="text" name="message">
                                                    <button id="${plan.scheduleID}" onclick="Commentit(id)">Send</button>
                                                    </div>
                                                </div>
                                            </div>
                                            <div style="text-align:right;">
                                                <svg onclick="alert('Make a Report Function')" class="user-svg" viewBox="0 0 16 16" title="report"><path d="M14.778.085A.5.5 0 0 1 15 .5V8a.5.5 0 0 1-.314.464L14.5 8l.186.464-.003.001-.006.003-.023.009a12.435 12.435 0 0 1-.397.15c-.264.095-.631.223-1.047.35-.816.252-1.879.523-2.71.523-.847 0-1.548-.28-2.158-.525l-.028-.01C7.68 8.71 7.14 8.5 6.5 8.5c-.7 0-1.638.23-2.437.477A19.626 19.626 0 0 0 3 9.342V15.5a.5.5 0 0 1-1 0V.5a.5.5 0 0 1 1 0v.282c.226-.079.496-.17.79-.26C4.606.272 5.67 0 6.5 0c.84 0 1.524.277 2.121.519l.043.018C9.286.788 9.828 1 10.5 1c.7 0 1.638-.23 2.437-.477a19.587 19.587 0 0 0 1.349-.476l.019-.007.004-.002h.001"></path></svg>
                                                <svg viewBox="0 0 16 16" class="user-svg" onclick="alert('UnLiked')">
                                                        <path
                                                            d="M6.956 14.534c.065.936.952 1.659 1.908 1.42l.261-.065a1.378 1.378 0 0 0 1.012-.965c.22-.816.533-2.512.062-4.51.136.02.285.037.443.051.713.065 1.669.071 2.516-.211.518-.173.994-.68 1.2-1.272a1.896 1.896 0 0 0-.234-1.734c.058-.118.103-.242.138-.362.077-.27.113-.568.113-.856 0-.29-.036-.586-.113-.857a2.094 2.094 0 0 0-.16-.403c.169-.387.107-.82-.003-1.149a3.162 3.162 0 0 0-.488-.9c.054-.153.076-.313.076-.465a1.86 1.86 0 0 0-.253-.912C13.1.757 12.437.28 11.5.28H8c-.605 0-1.07.08-1.466.217a4.823 4.823 0 0 0-.97.485l-.048.029c-.504.308-.999.61-2.068.723C2.682 1.815 2 2.434 2 3.279v4c0 .851.685 1.433 1.357 1.616.849.232 1.574.787 2.132 1.41.56.626.914 1.28 1.039 1.638.199.575.356 1.54.428 2.591z">
                                                        </path>
                                                </svg>
                                                <svg viewBox="0 0 28 16"  class="user-svg-larger" onclick="alert('Liked')">
                                                        <path d="M6.956 1.745C7.021.81 7.908.087 8.864.325l.261.066c.463.116.874.456 1.012.965.22.816.533 2.511.062 4.51a9.84 9.84 0 0 1 .443-.051c.713-.065 1.669-.072 2.516.21.518.173.994.681 1.2 1.273.184.532.16 1.162-.234 1.733.058.119.103.242.138.363.077.27.113.567.113.856 0 .289-.036.586-.113.856-.039.135-.09.273-.16.404.169.387.107.819-.003 1.148a3.163 3.163 0 0 1-.488.901c.054.152.076.312.076.465 0 .305-.089.625-.253.912C13.1 15.522 12.437 16 11.5 16H8c-.605 0-1.07-.081-1.466-.218a4.82 4.82 0 0 1-.97-.484l-.048-.03c-.504-.307-.999-.609-2.068-.722C2.682 14.464 2 13.846 2 13V9c0-.85.685-1.432 1.357-1.615.849-.232 1.574-.787 2.132-1.41.56-.627.914-1.28 1.039-1.639.199-.575.356-1.539.428-2.59z">
                                                        </path>
                                                </svg>

                                            </div>
                                        </div>

                                    </blockquote>
                                </details>
                                <small>${plan.endDate}</small>
                                
        `
        insideObject_li.innerHTML = userHeader;
        insideObject_li.appendChild(userBodyContainer)
        // MAIN CONTAINER
        calendarObjectList_Container.appendChild(insideObject_li)
        // ******* END FOR new
    }
}
//  ---------- COMMENT START --------------
// onchange = "Commentit(value,${plan.scheduleID})"
function Commentit(postID) {

    element = document.querySelector(`#input-${postID}`)
    if (element.value == '') {
        alert('InserT Comment')
        return
    }
    fetch(`/commentpost/${postID}`, {
        method: "POST",
        body: JSON.stringify({
            message: element.value,

        }),
    }).then(() => {
        element.value = '';
        // append the commend section
        CommentBuilder(postID)
    })

}
function CommentBuilder(postID) {
    CommentContainer = `comments-${postID}`
    CommentContainer = document.querySelector(`#${CommentContainer}`)
    CommentContainer.innerHTML = '';

    fetch(`/commentpost/${postID}`).then((response) => response.json()).then((data) => {
        for (i in data.commentList) {
            console.log(data.commentList[i])
            element = document.createElement('div')
            element.style.textAlign = 'left';
            element.innerHTML = `${data.commentList[i].messanger}:  ${data.commentList[i].message} `
            CommentContainer.appendChild(element)
        }
        console.log(data.commentList)
    })
}

//  ---------- COMMENT END --------------

function addReviewFromSchedulID(scheduleID) {
    // TODO ADD FETCH AND A FUNCTION TO ADD REVIEW
    // Removing the onlick review
    select = `#${scheduleID}`
    console.log('Splited: ', scheduleID.split('-')[1])
    scheduleIDreview = scheduleID.split('-')[1]
    // ADDING REVIEW
    fetch(`/addScheduleReview/${scheduleIDreview}`)
    document.querySelector(select).removeAttribute('onclick')
    return
}
function getPlan(whatPlan) { //USED ON HTML
    todaysMonth = parseInt(`{{currentMonth}}`)

    console.log('Fetching...d', todaysMonth)
    // PUT HERE THE LOADING
    fetch(whatPlan, {
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        // MAKE WHILE LOADING / FETCHING

    }).then(response => response.json()).then(data => {
        ii = 0
        for (d in data) {
            if (data[d].fields.monthN == todaysMonth) {
                new dateObjects(data[d].fields).createObject(data[d].fields)
                ii += 1
            }
        }
    }).then(() => {
        setTimeout(() => {
            showObjectListDIv()
        }, 500);
    })
    // ON load show objects
}


// ------------- END FOR CALENDAR AND OBJECTS -------------------------
