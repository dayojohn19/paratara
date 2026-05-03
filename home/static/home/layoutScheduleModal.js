
let currentStep = 1;
const totalSteps = 4;

function updateProgressBar() {
  let progressicon = document.getElementById("progressFill");
  const steps = document.querySelectorAll(".progress-step");
  const percent = ((currentStep - 1) / (totalSteps - 1)) * 100;
  progressicon.style.width = percent + "%";

  steps.forEach(step => {
    step.classList.toggle("active", parseInt(step.dataset.step) <= currentStep);
  });
}

// ✅ Disable validation on hidden steps
function setStepRequirements() {
  document.querySelectorAll(".step").forEach((step, index) => {
    const inputs = step.querySelectorAll("[required]");
    inputs.forEach(input => {
      if (index + 1 === currentStep) {
        input.disabled = false;
      } else {
        input.disabled = true;
      }
    });
  });
}

function nextStep() {
  const current = document.querySelector(`.step[data-step="${currentStep}"]`);
  const invalidField = current.querySelector(":invalid");

  if (invalidField) {
    // Show browser popup for the invalid field
    invalidField.reportValidity();

    // Optional: scroll into view if it's lower in the form
    invalidField.scrollIntoView({ behavior: "smooth", block: "center" });
    return; // Stop here — don’t go to next step
  }

  // If valid — proceed to next step
  current.classList.remove("active");
  currentStep++;
  const next = document.querySelector(`.step[data-step="${currentStep}"]`);
  if (next) next.classList.add("active");

  setStepRequirements();
  updateProgressBar();
}

function prevStep() {
  if (currentStep > 1) {
    document.querySelector(`.step[data-step="${currentStep}"]`).classList.remove("active");
    currentStep--;
    document.querySelector(`.step[data-step="${currentStep}"]`).classList.add("active");
    setStepRequirements();
    updateProgressBar();
  }
}

// Initialize


document.addEventListener("DOMContentLoaded", () => {
  setStepRequirements();
  updateProgressBar();
  const formschedule = document.querySelector("#schedule_form");

  formschedule.addEventListener("submit", (event) => {
    // just to see what happens before submission
    // enable everything before sending
    formschedule.querySelectorAll("[disabled]").forEach(input => {

      input.disabled = false;
    });


  });
});

