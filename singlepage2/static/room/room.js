let map;

function initMap() {
    map = new google.maps.Map(document.getElementById("map"), {
        center: { lat: 14.211279746038974, lng: 121.02127465910414 },
        zoom: 15,
    });

    new google.maps.Marker({
        position: { lat: 14.211279746038974, lng: 121.02127465910414 },
        map,
        title: "Resort Position !",
    })
}

 

function closeModal() {
    console.log('CLOSING OR OPENNING')
    dom = document.querySelector(".modal-container-main")
    if (dom.style.display == 'none') {
        dom.style.display = 'block'
    } else {
        dom.style.display = 'none'
    }
}
// TODO CHANGE
DATA_BASE_URL = 'http://127.0.0.1:8000/resortDB/1'
webID = 1
function SendGuestMessage() {
    guestContact = document.querySelector("#guest_contact").value
    if (guestContact == '') {
        return alert('Please Provide Contact')
    }
    guestMessage = document.querySelector("#guest_message").value
    if (guestMessage == '') {
        return alert('What is your Message')
    }

    fetch(DATA_BASE_URL, {
        method: 'POST',
        body: JSON.stringify({
            guestContact: guestContact,
            guestMessage: guestMessage,
            webID: webID
        })
    }).then(response => {
        alert('Message Sent')
    })
    sendEmail(guestContact, guestMessage, webID)
}
//  <script src="https://smtpjs.com/v3/smtp.js">
function sendEmail(guestContact, guestMessage, resortID) {
    Email.send({
        Host: "smtp.elasticemail.com",
        Username: "repapaka20@gmail.com",
        Password: "20B28409FAB2EC360F970DEBC62ACB854E4B",
        To: 'dayo_john16@yahoo.com',
        From: "repapaka20@gmail.com",
        Subject: `Resort ${resortID}: ${guestContact}`,
        Body: guestMessage
    }).then(
        message => alert('Please Check You Spam', message)
    );
}