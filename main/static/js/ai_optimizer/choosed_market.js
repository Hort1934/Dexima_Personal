const marketSelection = document.querySelector('.secondSection .market-selection')
let choosedExchange = null;
let s;
marketSelection.addEventListener('click', function(e){
    
    elem = e.target.closest('button');
    if (elem != null & marketSelection.contains(elem)){
    
        let connectA = elem.querySelector('.connectDiv a');
        if (connectA.innerText != "CONNECTED"){
         
            if(choosedExchange != elem.name || choosedExchange == null){
                let redirectToKeysPastPage = confirm("Keys ins't connected\nAre you want to connect?")
                if (redirectToKeysPastPage){
                    // let parts = connectA.href.split('/');
                    // let lastSegment = parts.pop() || parts.pop();
                    console.log(connectA)
                    window.location.href = connectA.href;
                }
            }
            
        }
        choosedExchange = elem.name;
    }
})