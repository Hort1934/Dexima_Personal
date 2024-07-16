const testDiv = document.querySelector('.infoVerify');
let currentModal = null;

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
    document.querySelector('.infoVerify').innerHTML = '';
    if (currentModal) {
        currentModal.remove();
    }
    let anError;
    let botId;
    let percentPNLFromOptimizer;
    let daysFromOptimizer;
    let usdtFromOptimizer;
    let leverageFromOptimizer;

    for (const prop in urls){
        let data = urls[prop];
        console.log(data)

        let request = fetching_data(data.url);
        let div = document.createElement('div');

        testDiv.insertAdjacentElement('beforeend', div);
        div.innerHTML = `${prop.replaceAll('_', ' ')}: `;
        showSpinner(div);

        let response = await request;
        let sp = findNearestSpinerInElem(div)
        let l = [];

        var keysToCheck = [data.key, data.key2, data.key3, data.key4, data.key5];

        keysToCheck.forEach(function(key) {
            if (response[key] !== undefined) {
                l.push(response[key]);
            }
        });
        if (prop == "Bot_creation"){
            botId = response[data.key];
        }
        if (prop == "Optimization"){
            percentPNLFromOptimizer = response[data.key2];
            daysFromOptimizer = response[data.key3];
            usdtFromOptimizer = response[data.key4];
            leverageFromOptimizer = response[data.key5];
            // let areUwantToContinueWithThisProfitConfirm = confirm(`In 30 days this strategy earned ${percentPNLFromOptimizer} percent profit`);
            let areUwantToContinueWithThisProfitConfirm = await customConfirm(
                `${daysFromOptimizer} Days / ${usdtFromOptimizer} USDT amount / ${leverageFromOptimizer} Leverage backtest result of this strategy is Profit +${percentPNLFromOptimizer}%, Drawdawn - _ _, _ _ %.`);
            if (!areUwantToContinueWithThisProfitConfirm){
                div.querySelector('span').remove()
                div.innerHTML += "There was an error while counting"
                let infoVerify = document.querySelector('.infoVerify');
                infoVerify.innerHTML = '';
                return;
            }
        }
        if (prop == "Account_status_checking"){
            if (!(l.every(e => e))) {
                sp.remove();
                div.innerHTML += "Your subscription has expired";
                anError = true;
                break;
            }
        }
        if (prop == "Available_ats_checking"){
            if (!(l.every(e => e))) {
                sp.remove();
                div.innerHTML += "No more available ATS";
                anError = true;
                break;
            }
        }
        if (prop == "API_Keys_checking"){
            if (!(l.every(e => e))) {
                sp.remove();
                div.innerHTML += "Error validating API keys";
                anError = true;
                break;
            }
        }
        if (prop == "Balance_checking"){
            if (!(l.every(e => e))) {
                sp.remove();
                div.innerHTML += "There is not enough money on your exchange balance";
                anError = true;
                break;
            }
        }
        if (prop == "Available_positions_and_orders_checking"){
            if (!(l.every(e => e))) {
                sp.remove();
                div.innerHTML += "You have open positions or orders for this currency";
                anError = true;
                break;
            }
        }
        if (prop == "Available_bots_checking") {
            if (!(l.every(e => e))) {
                sp.remove();
                div.innerHTML += "You already have a similar bot";
                anError = true;
                break;
            }
        }
        if (l.every(e => e) || prop == 'Bot_creation' && Number.isInteger(parseInt(response[data.key]))){
            sp.remove()
            div.innerHTML += "DONE"
        }else{
            sp.remove()
            div.innerHTML += "Error when starting the bot"
            anError = true;
            break;
        }
    }

    if (!anError){
        if (botId){
            await fetching_data(`/start_bot/${botId}`)
        }
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
      currentModal = modal;
  
      const confirmBtn = modal.querySelector('.confirm-btn');
      const cancelBtn = modal.querySelector('.cancel-btn');

      confirmBtn.addEventListener('click', () => {
        resolve(true);
        modal.remove();
        currentModal = null;
      });
  
      cancelBtn.addEventListener('click', () => {
        resolve(false);
        modal.remove();
        currentModal = null;
      });
    });
  }