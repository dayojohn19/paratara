window.onpopstate = function (event) {
  console.log(event)
  console.log('\n\n',event.state)
  // console.log(event.state.section);

  showPage(event.state.section);
};

function showPage(pageNumberID) {
  document.querySelectorAll(".main-container").forEach((element) => {
    element.style.display = "none";
  });
  document.querySelector(`#${pageNumberID}`).style.display = "block";
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".PageButton").forEach((button) => {
    button.onclick = function () {
      const PageNumberSection = this.dataset.page;
      //   Changing URL
      //   history.pushState({ section: PageNumberSection }, "", `section_${PageNumberSection}`);
      //   Manipulate domain
      history.pushState({ section: PageNumberSection }, "", ``);
      showPage(PageNumberSection);
    };
  });
});

function FetchURL(URL_fetch) {
  // In Python
  // URL
  // path("https://mainurl/URL_fetch", views.command, name='command')
  // views
  // return HttpResponse(texts)
  // else:
  // raise Http404("No such Page")
  fetch(`https://mainurl/${URL_fetch}`)
    .then((response) => response.text())
    .then((text) => {
      console.log(text);
      // Use Text
    });
}
