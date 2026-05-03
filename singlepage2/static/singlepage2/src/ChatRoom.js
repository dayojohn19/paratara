function requestDeleteMessage(Message_delete_request) {
  console.log("Message to Delete: ", Message_delete_request);
}

async function registerUserThroughJSON(elementData) {
  console.log("Just getting the log", elementData[0], elementData[1]);
  const returnedResponse = await fetch("/userProfile/registerjson", {
    headers: { "X-CSRFToken": csrftoken },
    method: "POST",
    body: JSON.stringify({
      username: elementData[0],
      contact: elementData[1],
      password: elementData[0],
      passwordConfirmation: elementData[0],
    }),
  });

  const returnedResponseJson = await returnedResponse.json();

  if (returnedResponseJson[0].search("taken")) {
    localStorage["user_user_json"] = elementData[0];
    localStorage["user_pass_json"] = elementData[0];
    localStorage["user_contact_json"] = elementData[1];
  } else {
    new_user_nickname = prompt("Username Already Taken");
    localStorage["userinputnickname"] = new_user_nickname;
    chat_room_created.user_username = new_user_nickname;

    localStorage["user_pass_json"] = new_user_nickname.split(/\W+/).join("");
    localStorage["user_user_json"] = localStorage["user_pass_json"];
    new_user_contact = elementData[1];

    registerUserThroughJSON([localStorage["user_pass_json"], new_user_contact]);
    return;
  }

  alert(returnedResponseJson[0], elementData[0]);
}

function Chat_Roomm(room_name = null, user_contact = null, user_username = null) {
  if (room_name == null) {
    this.room_name = prompt("Room Name: ").split(/\W+/).join("_");
  } else {
    this.room_name = room_name.split(/\W+/).join("_");
  }

  do {
    if (localStorage["userinputnickname"] == null) {
      console.log("No record Found");
      this.user_username = prompt("Nickname : ");

      // Checking if has Special Character
      format = /[!@#$%^&*()+\-=\[\]{};':"\\|,.<>\/?]+/;
      if (!format.test(this.user_username)) {
        console.log("Your Username is right", this.user_username);
      } else {
        console.log(this.user_username);
        alert("Please Choose easy Nickname ");
        console.log("Your Username is Wrong", this.user_username);
        new Chat_Roomm(this.room_name);
        return;
      }

      this.user_user_json = this.user_username.split(/\W+/).join("");
      this.user_pass_json = this.user_user_json;
      if (user_contact == null) {
        this.user_contact_json = prompt("Your Contact Number or Email");
      } else {
        this.user_contact_json = user_contact;
      }

      registerUserThroughJSON([this.user_user_json, this.user_contact_json]);

      // localStorage["user_user_json"] = this.user_user_json;
      // localStorage["user_pass_json"] = this.user_pass_json;
      // localStorage["user_contact_json"] = this.user_contact_json;

      localStorage["userinputnickname"] = this.user_username;
    } else {
      console.log("record Found Old Nickname in Local Storage");

      this.user_username = localStorage["userinputnickname"];
      this.user_user_json = localStorage["user_user_json"];
      this.user_pass_json = localStorage["user_pass_json"];

      registerUserThroughJSON([this.user_user_json, this.user_contact_json]);
    }

    // registerUserThroughJSON([this.user_username, this.user_user_json]);

    // console.log("Local Storage Null", localStorage["userinputnickname"]);
    // do {
    //   localStorage["userinputnickname"] = this.user_username;
    //   console.log("Username Null", localStorage["userinputnickname"]);
    //   console.log("Username Null", this.user_username);
    // } while (localStorage["userinputnickname"] == null);
    // this.user_username = prompt("Your Nickname: ").split(/\W+/).join(" ");
  } while (localStorage["userinputnickname"] == null);

  // this.base_url = "professional-website-2a09915461ba.herokuapp.com";
  // this.base_url = "http://127.0.0.1:8000";
  this.base_url = window.location.host;
  // this.base_url = "https://dayojohn19-django--8000.prod1a.defang.dev";
  
  //   Creating Room Container
  this.room_container = document.createElement("div");
  this.room_container.setAttribute("class", "container bg-body-tertiary rounded single-chat-room");
  this.Form_Object = document.createElement("form");
  this.Form_Object.setAttribute("id", `Chat_Message_Form_${this.room_name}`);
  this.Form_Object.setAttribute("class", `form_message_input_box`);
  this.Form_Object.innerHTML = `
  <div class="col-md-6">
    <div class="input-group">
      <input style="font-family:LaishaFontStyle" id="Chat_Message_Input_${this.room_name}" type="text" name="message" class="form-control" placeholder="Message" aria-label="Input group example" aria-describedby="basic-addon1" required />
      <button type="submit" class="btn btn-primary" id="Chat_Message_Send_Button" style="margin: 0 auto">
        <svg width="16" height="16" fill="currentColor" class="bi bi-chat" viewBox="0 0 16 16">
          <path d="M2.678 11.894a1 1 0 0 1 .287.801 10.97 10.97 0 0 1-.398 2c1.395-.323 2.247-.697 2.634-.893a1 1 0 0 1 .71-.074A8.06 8.06 0 0 0 8 14c3.996 0 7-2.807 7-6 0-3.192-3.004-6-7-6S1 4.808 1 8c0 1.468.617 2.83 1.678 3.894zm-.493 3.905a21.682 21.682 0 0 1-.713.129c-.2.032-.352-.176-.273-.362a9.68 9.68 0 0 0 .244-.637l.003-.01c.248-.72.45-1.548.524-2.319C.743 11.37 0 9.76 0 8c0-3.866 3.582-7 8-7s8 3.134 8 7-3.582 7-8 7a9.06 9.06 0 0 1-2.347-.306c-.52.263-1.639.742-3.468 1.105z"></path>
        </svg>
        Send
      </button>
    </div>
  </div>
  `;
  console.log('Socket HTML MAde')
  this.Form_Object.addEventListener("submit", (e) => {
    e.preventDefault();
    let message = e.target.message.value;
    this.chatSocket.send(
      JSON.stringify({
        message: [message, this.user_username],
        username: `${this.user_username}`,
      })
    );
    this.Form_Object.reset();
  });

  this.Form_Object.insertAdjacentHTML("beforeend", `<h1 class="text-primary-emphasis">${this.room_name.split("_").join(" ")}</h1>`);
  this.room_message_container = document.createElement("div");
  this.room_message_container.setAttribute("id", `Chat_Message_Container_${this.room_name}`);
  this.room_container.appendChild(this.room_message_container);
  this.room_messages_box = document.createElement("div");
  this.room_messages_box.setAttribute("id", `room_messages_box_${this.room_name}`);
  this.room_container.appendChild(this.room_messages_box);
  console.log('Making Spinner')
  this.loading_spinnger = `             
  <div class="alert alert-primary m-5" role="alert">
  <div class="spinner-grow text-primary " role="status"></div>
  Connecting to <a href="#" class="alert-link">${this.room_name.split("_").join(" ")}</a>
  <div class="spinner-grow text-secondary" role="status"></div>
                                        <div class="spinner-border spinner-border-sm" role="status">
                                        </div>                                        
                                        `;
  this.room_messages_box.innerHTML = this.loading_spinnger;
  console.log('Loading Chat Room');
  // Creating Socket
  var loc = window.location, new_uri;
  if (loc.protocol === "https:") {
    new_uri = "wss";
  } else {
    new_uri = "ws";
  }
  console.log('We Got URI: ',new_uri);
  this.socket_url = `${new_uri}://${this.base_url}/${new_uri}/${this.room_name}/socket-server/`;
  console.log('Socket on: ',this.socket_url);
  // this.socket_url = 'ws://127.0.0.1:8000/ws/_Public_Chat_/socket-server/';
  this.chatSocket = new WebSocket(this.socket_url);
  console.log(this.chatSocket,'\n\n Socket Chat Created');
  this.AppendNewChatContainer = () => {
    // Querying the Page to Append
    ChatRoomContainer = document.getElementById("main-container-page-3");
    ChatRoomContainer.appendChild(this.room_container);
  };
  this.AppendNewChatContainer();
  this.autoMessage = (automatedMessage) => {
    console.log('Sending Socket.... ');
    this.chatSocket.send(
      JSON.stringify({
        message: [automatedMessage, this.user_username],
        username: `${this.user_username}`,
      })
    );
    alert("Wait or contact directly");
  };
  // this.chatSocket.onerror = () => {
  this.chatSocket.onerror = (e) => {
    console.log('Sending Socket Error.. ',e);
    console.error("WebSocket error observed:", e);
    setTimeout(() => {
      this.room_messages_box.innerHTML = `
      <div class="alert alert-warning" role="alert">
      Connecting to  <a href="#" class="alert-link">${this.room_name.split("_").join(" ")}</a>. 
      Failed
      <button class='btn btn-primary' onclick="${this.chatSocket.OPEN};location.reload();">Reload the page</button>
      </div>`;
    }, 10000);
  };

  this.chatSocket.onopen = () => {
    console.log('Socket Opened..')
    this.chatSocket.send(
      JSON.stringify({
        message: ["Joined the Room", this.user_username],
        username: `${this.user_username}`,
      })
    );

    console.log("You Connected", this.user_username);

    this.room_messages_box.innerHTML = "";
    this.room_container.appendChild(this.Form_Object);

    this.chatSocket.onclose = () => {
      setTimeout(() => {
        `             
  <div class="alert alert-danger m-5" role="alert">
  <div class="spinner-grow text-primary " role="status"></div>
  Reconnecting to <a href="#" class="alert-link">${this.room_name.split("_").join(" ")}</a>
  <div class="spinner-grow text-secondary" role="status"></div>
                                        <div class="spinner-border spinner-border-sm" role="status">
                                        </div>                                        
                                        `;
      }, 2000);
    };
  };

  this.chatSocket.onmessage = (e) => {
    data = JSON.parse(e.data);
    // Input for User Image the line after href
    // <img src="https://github.com/twbs.png" alt="twbs" width="32" height="32" class="rounded-circle flex-shrink-0" />
    this.item_message_container = `
          <a href="#" class="list-group-item list-group-item-action d-flex gap-3 py-3" aria-current="true">
            
            <div class="d-flex gap-2 w-100 justify-content-between">
              <div>
                <h6 style="text-align:left" class="mb-0">${data.username}:</h6>
                <p class="mb-0 opacity-75">${data.message.split("_").join(" ")}</p>
              </div>
              <small class="opacity-50 text-nowrap">${data.message_timestamp}</small>
            </div>
          </a>
          `;
    if (data.type === "chat") {
      this.room_message_container.innerHTML += this.item_message_container;
      this.room_message_container.scrollTo(0, this.room_message_container.scrollHeight);
    }
  };

  return this;
}

//
//
//
//
//
//
//
// BACKUP
function Chat_RoommBACKUP(room_name) {
  this.room_name = room_name;
  //   Creating Room Container
  this.this.room_container = document.createElement("div");
  this.room_container.setAttribute("class", "bg-body-tertiary p-5 rounded");
  this.room_container.innerHTML = `  <h1>Room Name ${this.room_name}</h1>
      <div id="Chat_Message_Container_${this.room_name}"></div>`;
  this.Form_Object = document.createElement("form");
  this.Form_Object.setAttribute("id", `Chat_Message_Form_${this.room_name}`);
  this.Form_Object.innerHTML = `
    <div class="col-md-6">
      <div class="input-group">
        <input id="Chat_Message_Input_${this.room_name}" type="text" name="message" class="form-control" placeholder="Message" aria-label="Input group example" aria-describedby="basic-addon1" required />
        <button type="submit" class="btn btn-primary" id="Chat_Message_Send_Button" style="margin: 0 auto">
          <svg width="16" height="16" fill="currentColor" class="bi bi-chat" viewBox="0 0 16 16">
            <path d="M2.678 11.894a1 1 0 0 1 .287.801 10.97 10.97 0 0 1-.398 2c1.395-.323 2.247-.697 2.634-.893a1 1 0 0 1 .71-.074A8.06 8.06 0 0 0 8 14c3.996 0 7-2.807 7-6 0-3.192-3.004-6-7-6S1 4.808 1 8c0 1.468.617 2.83 1.678 3.894zm-.493 3.905a21.682 21.682 0 0 1-.713.129c-.2.032-.352-.176-.273-.362a9.68 9.68 0 0 0 .244-.637l.003-.01c.248-.72.45-1.548.524-2.319C.743 11.37 0 9.76 0 8c0-3.866 3.582-7 8-7s8 3.134 8 7-3.582 7-8 7a9.06 9.06 0 0 1-2.347-.306c-.52.263-1.639.742-3.468 1.105z"></path>
          </svg>
          Send
        </button>
      </div>
    </div>
    `;
  this.Form_Object.addEventListener("submit", (e) => {
    e.preventDefault();
    let message = e.target.message.value;
    chatSocket.send(
      JSON.stringify({
        message: [message, this.user_username],
        username: `${this.user_username}`,
        message: message,
      })
    );
    form.reset();
  });

  this.room_container.appendChild(this.Form_Object);

  this.AppendNewChatContainer = () => {
    console.log("Appending");
    ChatRoomContainer = document.getElementById("main-container-page-3");
    // this.room_container.insertAdjacentHTML("beforeend", this.room_form);
    // this.room_container.append(this.room_form);
    // ChatRoomContainer.insertAdjacentHTML("beforeend", this.room_container);
    ChatRoomContainer.appendChild(this.room_container);

    console.log("Done Appending..");
  };

  this.AppendNewChatContainer();
}
