// JavaScript will go here
// script.js

// Function to validate booking form
function validateBookingForm() {
    const name = document.forms["bookingForm"]["name"].value;
    const phone = document.forms["bookingForm"]["phone"].value;
    const members = document.forms["bookingForm"]["members"].value;
    const farmhouse = document.forms["bookingForm"]["farmhouse"].value;
    const visitDate = document.forms["bookingForm"]["visit_date"].value;
    const advance = document.forms["bookingForm"]["advance"].value;

    if (!name || !phone || !members || !farmhouse || !visitDate || !advance) {
        alert("All fields must be filled out.");
        return false;
    }
    return true;
}

// Attach the validation function to the form submission
document.addEventListener("DOMContentLoaded", function() {
    const form = document.querySelector("form");
    form.onsubmit = function() {
        return validateBookingForm();
    };
});
