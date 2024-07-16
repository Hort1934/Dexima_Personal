const testDiv = document.querySelector('.infoVerify');

function findNearestSpinerInElem(elem){
    let spinnerElems = elem.querySelectorAll('.spinner-border');
    return spinnerElems[spinnerElems.length-1];
}

function showSpinner(button) {
    spinner.classList.add('spinner-border', 'spinner-border-sm');
    spinner.setAttribute('role', 'status');
    spinner.setAttribute('aria-hidden', 'true');
    button.appendChild(spinner);
    return this;
}
async function fetching_data(url){
    return fetch(url)
        .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
        })
        .then(data => {
            return data;
        })
        .catch(error => {
            console.error('Error:', error.message);
        });
};


async function fullfillInfoDiv(urls){
    let anError;
    let botId;
    let percentPNLFromOptimizer;

    for (const prop in urls){
        let data = urls[prop];

        let request = fetching_data(data.url);
        let div = document.createElement('div');

        testDiv.insertAdjacentElement('beforeend', div);
        div.innerHTML = `${prop.replaceAll('_', ' ')}: `;
        showSpinner(div);

        let response = await request;
        let sp = findNearestSpinerInElem(div)
        let l = [];

        l.push(response[data.key])
        if (response[data.key2] != undefined){
            l.push(response[data.key2])
        }

        if (prop == "Bot_creation"){
            botId = response[data.key];
        }
        if (prop == "Optimization"){
            percentPNLFromOptimizer = response[data.key2];
            // let areUwantToContinueWithThisProfitConfirm = confirm(`In 30 days this strategy earned ${percentPNLFromOptimizer} percent profit`);
            let areUwantToContinueWithThisProfitConfirm = await customConfirm(`30 days backetest result, of this strategy is ${percentPNLFromOptimizer}%`);
            if (!areUwantToContinueWithThisProfitConfirm){
                div.querySelector('span').remove()
                div.innerHTML += "ERROR"
                let infoVerify = document.querySelector('.infoVerify');
                infoVerify.innerHTML = '';
                return;
            }
        }
        if (l.every(e => e) || prop == 'Bot_creation' && Number.isInteger(parseInt(response[data.key]))){
            sp.remove()
            div.innerHTML += "DONE"
        }else{
            sp.remove()
            div.innerHTML += "ERROR"
            anError = true;
            break;
            // TODO make error massege
        }
    }

    if (!anError){
        await fetching_data(`/start_bot/${botId}`)
    }
    return !anError;
};


function customConfirm(message) {
    return new Promise(resolve => {
      const modal = document.createElement('div');
      modal.className = 'custom-confirm';
      modal.innerHTML = `
        <div class="message">${message}</div>
        <div class="modalFlex">
        <button class="confirm-btn">Create Bot</button>
        <button class="cancel-btn">Cancel</button>
        </div>
      `;
      
      document.body.appendChild(modal);
  
      const confirmBtn = modal.querySelector('.confirm-btn');
      const cancelBtn = modal.querySelector('.cancel-btn');
  
      confirmBtn.addEventListener('click', () => {
        resolve(true);
        modal.remove();
      });
  
      cancelBtn.addEventListener('click', () => {
        resolve(false);
        modal.remove();
      });
    });
  }