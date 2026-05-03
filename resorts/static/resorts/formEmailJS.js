

import { emailjs } from "https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js";
(function() {
    // https://dashboard.emailjs.com/admin/account
    emailjs.init({
      publicKey: "kPR5fCmH0j3E0NSyr",
    });
})();


// <!-- 
    
// This side is Email JS Contact Form 
// ⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎⬇︎ Add all the code below this to HTml File

// -->
// <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>
// <script type="text/javascript">
 
// </script>
// <script type="text/javascript">
//     window.onload = function() {
//         document.getElementById('contact-form').addEventListener('submit', function(event) {
          
//           (function() {
//         // https://dashboard.emailjs.com/admin/account
//         emailjs.init({
//           publicKey: "kPR5fCmH0j3E0NSyr",
//         });
//     })();
//             event.preventDefault();
//             console.log('Printing This: ',this)
//             // these IDs from the previous steps
//             emailjs.send('service_wizvf4w', 'template_7znistv', {name:'NameTestTemplate',notes:'NotesTest fomr template param'})
//             // emailjs.sendForm({serviceID:'service_9uqpnxq'}, {templateID:'template_ifyyi4c'}, this)
//                 .then(() => {
//                     console.log('SUCCESS!');
//                 }, (error) => {
//                     console.log('FAILED...', error);
//                 });
//         });
//     }
// </script>
// <form id="contact-form">
//   <!-- To simplify the tutorial, the value is static. -->
//   <input type="hidden" name="contact_number" value="697483">
//   <label>Name</label>
//   <input type="text" name="user_name">
//   <label>Email</label>
//   <input type="email" name="user_email">
//   <label>Message</label>
//   <textarea name="message"></textarea>
//   <input type="submit" value="Send">
// </form>
// <!-- ⬆︎⬆︎⬆︎This side is Email JS Contact Form ⬆︎⬆︎⬆︎ -->

