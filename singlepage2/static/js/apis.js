function API_test() {
  fetch("http://127.0.0.1:8000/REST_API_app/", {
    headers: { "X-CSRFToken": csrftoken, Accept: "application/json", "Content-Type": "application/json" },
    method: "GET",
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
    });
}
