window.addEventListener("DOMContentLoaded", function () {
  console.log("\n\n\n------------------------------\n");
  console.log("static/js/scrollChecker.js\n\n");
  // Continuos scrolling
  try {
    window.onscroll = () => {
      if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
        console.log("You Reach the Bottom");
        // window.dispatchEvent("DOMContentLoaded");

        modalButtonClick = document.querySelector('button[name="ReachingBottomPageModal"]');
        modalButtonClick.click();
        modalButtonClick.remove();
      }
    };

    // code that throws the error
  } catch (e) {
    // exit the loop
    console.log(e);
  }

  console.log("User Scrolling: ");
  console.log(window.scrollY);
  console.log(window.innerHeight);
  console.log("\n------------------------------\n");
});

var csrftoken = window.drf.csrfToken;
