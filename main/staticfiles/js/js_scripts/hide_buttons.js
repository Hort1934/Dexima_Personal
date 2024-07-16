window.addEventListener('DOMContentLoaded', function(){


  const centerContent = document.querySelector("main .center-content");
  const firstSectionButtons = centerContent.querySelectorAll(".market-selection button");
  const strategySelectionBtns = document.querySelectorAll('.strategy-selection button');
  
  
  firstSectionButtons.forEach(function(button) {
    
    button.addEventListener("click", function(event) {
      let buttons = this.parentElement.querySelectorAll('button');
      event.preventDefault();
  
      // Remove the class from other buttons
      buttons.forEach(function(otherButton) {
        if (otherButton !== button) {
          otherButton.classList.toggle("hidden1");
          setTimeout(function() {
            
          otherButton.classList.toggle("displayNone");
          }, 550);
        }
      });
  
      let notHiddenBtnsArray = [...buttons].map(function (btn) {
          return !btn.classList.contains('hidden1')
      }) 
      let notHiddenBtn = notHiddenBtnsArray.every(item => item === true)
  
      let nextSection = this.parentElement.parentElement.nextElementSibling
  
      if (notHiddenBtn){
        while(true){
          if (!nextSection.classList.contains('section')){
            break;
          }
          let local_btns = nextSection.querySelectorAll('button')
          local_btns.forEach(function(btn){
            setTimeout(function() {
              btn.classList.remove('hidden1')
              btn.classList.remove("displayNone");
              }, 550);          
          });
          
          nextSection.classList.add('hidden1');
          nextSection = nextSection.nextElementSibling;
        }
      }else{
          nextSection.classList.toggle('hidden1');
      }
    });
  
  });
  
  
  
  strategySelectionBtns.forEach(function(btn){
    btn.addEventListener("click", function(){
      strategySelectionBtns.forEach(function(otherButton) {
        if (otherButton !== btn) {
          otherButton.classList.toggle("hidden1");
          setTimeout(function() {
            
            otherButton.classList.toggle("displayNone");
            }, 550);
          
        }
      })
    })
  })
  
  })