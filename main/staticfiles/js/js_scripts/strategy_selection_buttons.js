const strategySelectionDiv = document.querySelector('.strategy-selection');
const strategyButtons = strategySelectionDiv.querySelectorAll('button');
const fourthSection = document.querySelector('.fourthSection');

const dashbordBtn = document.querySelector('#dashbordBtn');

let minQuantityInfo = null;
let total_investment = document.querySelector("#total_investment");
let leverage= document.querySelector("#leverage");

async function getMinimalQuantity(symbol){
    const url = `/get_minimal_quantity/${symbol}/`;
    
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


strategyButtons.forEach(async function(button){
    button.addEventListener('click',async function(el){

        showSpinner(fourthSectionWaitForAction)
        minQuantityInfo = await getMinimalQuantity(choosedSymbol.textContent);


        total_investment.dataset.originalMin = minQuantityInfo.min_total;
        total_investment.dataset.originalMax  = minQuantityInfo.max_total;

        total_investment.min = minQuantityInfo.min_total;
        total_investment.max = minQuantityInfo.max_total;
        leverage.min = minQuantityInfo.min_leverage;
        leverage.max = minQuantityInfo.max_leverage;
        total_investment.value = minQuantityInfo.min_total
        leverage.value = minQuantityInfo.min_leverage
        
        leverage.placeholder = `min: ${minQuantityInfo.min_leverage} max: ${minQuantityInfo.max_leverage}`
        total_investment.placeholder = `min: ${minQuantityInfo.min_total} max: ${minQuantityInfo.max_total}`

        chosedStrategy = button.name;
        
        //clen spinner
        fourthSectionWaitForAction.innerHTML = '';

        fourthSection.classList.remove('hidden1')
    })
})

dashbordBtn.addEventListener("click", async function(e){

    let marginTypeValue  = document.querySelector("#margin_type").value;
    let chosen_asset = choosedSymbol.textContent;

    
    
    "DONT TOUCH this COMMENT if Jenya will change his mind"
    let urls = {
        'API_Keys_checking': {
            'url': "/check_user_api_keys/",
            'key': 'keys_saved',
        },
        'Balance_checking': {
            'url': `/check_balance/?total_investment=${total_investment.value}`,
            'key': 'enough_balance',
        },
        'Available_positions_and_orders_checking': {
            'url': `/check_pos_and_orders/?chosen_asset=${chosen_asset}`,
            'key': 'no_positions',
            "key2": 'no_orders'
        },
        'Optimization': {
            'url': `/crypto_optimize/?chosen_strategy=${chosedStrategy}&chosen_asset=${chosen_asset}&chosen_exchange=bybit&total_investment.value=${total_investment.value}`,
            'key': 'optimization_completed',
            'key2': 'pnl',
        },
        'Bot_creation': {
            'url': `/create_bot/?marker=quick_start&chosen_market=crypto&chosen_strategy=${chosedStrategy}&chosen_exchange=bybit&chosen_asset=${chosen_asset}&total_investment=${total_investment.value}&leverage=${leverage.value}&margin_type=${marginTypeValue}`,
            'key': 'strategy_id',
        },
    };
    if (checkMinimalQuantityParam(total_investment.value, leverage.value, marginTypeValue)){
        let isDone = await fullfillInfoDiv(urls);
            if(isDone)
                window.location.href = '/dashboard';
    }


})
// add_to_dashboard/?chosen_market=crypto&chosen_exchange=binance&chosen_asset=BTCUSDT&chosen_strategy=f1&total_investment=1000&leverage=1&margin_type=IZOTALED
function checkMinimalQuantityParam(totalInvestmentInput, leverageInput, marginTypeInput){
    if (
            totalInvestmentInput >= minQuantityInfo.min_total 
            && minQuantityInfo.min_leverage < leverageInput < minQuantityInfo.max_leverage
            && marginTypeInput == "ISOLATED" || marginTypeInput == "CROSS"
        ){
        return true;
    }
    return false;
}

// todo move it or replace. must be in 1 file
const spinner = document.createElement('span');

function showSpinner(button) {
    spinner.classList.add('spinner-border', 'spinner-border-sm');
    spinner.setAttribute('role', 'status');
    spinner.setAttribute('aria-hidden', 'true');
    // button.innerHTML = '';
    button.appendChild(spinner);
}

[total_investment, leverage].forEach(function(input){
    input.addEventListener('input', allowOnlyDigit);
    input.addEventListener('focusout', checkMinMaxInputValue);
});

leverage.addEventListener('input', function(e){
    let value = (this.value === '') ? 1 : this.value;
    total_investment.min = ((total_investment.dataset.originalMin / value) > 1) ? (total_investment.dataset.originalMin / value).toFixed(1) : 1;
    checkMinMaxInputValue.call(total_investment);
    let placeholderToTotalInvestment = `min: ${total_investment.min} max: ${total_investment.max}`;
    total_investment.placeholder = placeholderToTotalInvestment;
    total_investment.parentElement.querySelector('.errMsgTxt').innerHTML = placeholderToTotalInvestment;
});

function allowOnlyDigit(){
    this.value = this.value.replace(/[^\d.]/g, '');
}
