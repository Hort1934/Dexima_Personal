      // var centerContent = document.querySelector("main .center-content")
      // var firstSectionButtons = centerContent.querySelectorAll(".market-selection button")

      
      // firstSectionButtons.forEach(function(button) {
      //     button.addEventListener("click", function(event) {
      //       console.log(111)
      //       let buttons = this.parentElement.querySelectorAll('button');
      //       event.preventDefault();
            
      //       // Remove the class from other buttons
      //       buttons.forEach(function(otherButton) {
      //         if (otherButton !== button) {
      //           otherButton.classList.toggle("hidden1");
      //           setTimeout(function() {
      //             // Добавляем класс "hidden1" через 1 секунду
      //             otherButton.style.display = 'none';

      //             // Если нужно использовать display: none, то можно использовать следующую строку:
      //             // otherButton.style.display = "none";
      //           }, 5000);

      //         }
      //       });

      //       let notHiddenBtnsArray = [...buttons].map(function (btn) {
      //           return !btn.classList.contains('hidden1')
      //       }) 
      //       let notHiddenBtn = notHiddenBtnsArray.every(item => item === true)

      //       let nextSection = this.parentElement.parentElement.nextElementSibling

      //       if (notHiddenBtn){
      //         while(true){
      //           if (!nextSection.classList.contains('section')){
      //             break;
      //           }
      //           let local_btns = nextSection.querySelectorAll('button')
      //           local_btns.forEach(function(btn){
      //             btn.classList.remove('hidden1')
      //           })
      //           nextSection.classList.add('hidden1');
      //           nextSection = nextSection.nextElementSibling;

      //         }
      //       }else{
      //           nextSection.classList.toggle('hidden1');
      //       }
      //     });



      //   });