const selectBtnMarket = document.querySelector("#market");
const selectBtnExchange = document.querySelector("#exchange");
const selectBtnAsset = document.querySelector("#asset");
const selectBtnAmount = document.querySelector("#amount");
const selectBtnLeverage = document.querySelector("#leverage");
const selectBtnStrategy = document.querySelector("#strategy");
const selectBtnTimeframe = document.querySelector("#timeframe");
const dateFrom = document.querySelector("#from_date");
const dateTo = document.querySelector("#to_date");

const backtestBtn = document.querySelector("#backtestBtn");
const aiOptimizerBtn = document.querySelector("#aiOptimizerBtn");

const addToDashboardBtn = document.querySelector("#addToDashboardBtn");


let dt;
let chosenSymbol;
console.log(123)
// calculate and past minimal sum invest in investment input; leverage;
selectBtnAsset.addEventListener("change", async function (e) {
    chosenSymbol = this.value;

    selectBtnAsset.disabled = true;
    let minQuantityInfo = await getMinimalQuantity(chosenSymbol);
    selectBtnAsset.disabled = false;

    selectBtnAmount.min = minQuantityInfo.min_total;
    selectBtnAmount.max = minQuantityInfo.max_total;
    selectBtnLeverage.min = minQuantityInfo.min_leverage;
    selectBtnLeverage.max = minQuantityInfo.max_leverage;
    selectBtnAmount.placeholder = `min ${minQuantityInfo.min_total} max ${minQuantityInfo.max_total}`
    selectBtnLeverage.placeholder = `min ${minQuantityInfo.min_leverage} max ${minQuantityInfo.max_leverage}`
});


// backtestBtn.addEventListener("click", async function (e) {
//     let assetVal = document.querySelector('#asset').value;
//     let strategy =  document.querySelector('#strategy').value;
//     let dataFromTable = parseTable();
//
//     let grids = dataFromTable.num_of_grids ? dataFromTable.num_of_grids.value : "10";
//     console.log(grids, 'numofGRIDS||||||||||||')
//     let timeframe = dataFromTable.timeframe ? dataFromTable.timeframe.value : "1m";
//     let price_range = dataFromTable.price_range ? dataFromTable.price_range.value : "12";
//     let activation_trigger_in_percent = dataFromTable.activation_trigger_in_percent ? dataFromTable.activation_trigger_in_percent.value : "1.0";
//     let distribution_of_grid_lines = dataFromTable.distribution_of_grid_lines ? dataFromTable.distribution_of_grid_lines.value : "LINEAR";
//     let short_stop_loss_in_percent = dataFromTable.short_stop_loss_in_percent ? dataFromTable.short_stop_loss_in_percent.value : "1.0";
//     let long_stop_loss_in_percent = dataFromTable.long_stop_loss_in_percent ? dataFromTable.long_stop_loss_in_percent.value : "1.0";
//     let trend_period = dataFromTable.trend_period ? dataFromTable.trend_period.value : "1.0";
//     // console.log(dataFromTable)
//
//     const url = `/get_bybit_backtest_and_optimization_params/?symbol=${assetVal}&strategy=${strategy.value}&leverage=${leverage.value}&num_of_grids=${grids}&available_balance=${amount.value}&timeframe=${timeframe}&price_range=${price_range}&activation_trigger_in_percent=${activation_trigger_in_percent}&distribution_of_grid_lines=${distribution_of_grid_lines}&line_disbalance_direction=ASCENDING&short_stop_loss_in_percent=${short_stop_loss_in_percent}&long_stop_loss_in_percent=${long_stop_loss_in_percent}&grid_disbalance_direction=ASCENDING&trend_period_timeframe=1h&trend_period=${trend_period}&from=${from_date.value}&to=${to_date.value}`;
//     const backtestTableBody = document.querySelector("#backtestResults tbody");
//     console.log(url, '679')
//     let backtestData = await fetching_data(url);
//     // alert(JSON.stringify(backtestData, null, 2));
//     // document.getElementById("result").textContent = JSON.stringify(backtestData, null, 2);
//     // todo seperate in another function
//     // let btnTextContent = backtestBtn.textContent;
//     // backtestBtn.textContent = "";
//     // showSpinner(backtestBtn);
//     // backtestBtn.disabled = true;
//     fillBacktestOrOptimizerTable(backtestData, backtestTableBody);
//     // backtestBtn.textContent = btnTextContent;
//     // backtestBtn.disabled = false;
//
// });


// TODO remove it and import from anouther file
async function getMinimalQuantity(symbol) {
    let url;
    if (exchange.value == "Binance") {
        url = `/get_minimal_quantity/${symbol}/`;
    } else {
        url = `/get_bybit_open_order_rules/?symbol=${symbol.toLocaleLowerCase()}`;
    }
    return fetching_data(url);
};

function fillBacktestOrOptimizerTable(backtestData, backtestTableBody) {
    // const backtestTableBody = document.querySelector("#backtestResults tbody");
    backtestTableBody.innerHTML = "";
    let startBalance = null;

    for (const key in backtestData) {
        console.log(key)
        if (backtestData.hasOwnProperty(key)) {

            const row = document.createElement("tr");
            const th = document.createElement("th");
            const td = document.createElement("td");

            th.textContent = key;
            td.textContent = backtestData[key];

            row.appendChild(th);
            row.appendChild(td);

            changeColorInTableData(td, key, startBalance);

            backtestTableBody.appendChild(row);
        }
    }
}

// aiOptimizerBtn.addEventListener("click", async function (e) {
//     debugger;
//     let assetVal = document.querySelector('#asset').value;
//     const requestData = {
//         symbol: asset.value,
//         leverage: leverage.value,
//         available_balance: amount.value,
//         from_date: from_date.value,
//         to_date: to_date.value,
//         data: parseTable()
//     };
//
//     const url = `/get_bybit_backtest_and_optimization_params/?requestData=${JSON.stringify(requestData)}`;
//
//
//     const backtestTableBody = document.querySelector("#backtestResults tbody");
//
//     let backtestData = await fetching_data(url);
//     alert(JSON.stringify(backtestData, null, 2));
//
// })


async function fetching_data(url) {

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
}


function changeColorInTableData(tableData, tableHeadName, startBalance) {
    let FloatValueMatch = tableData.textContent.match(/\d+/)
    let floatValue = (FloatValueMatch) ? parseFloat(FloatValueMatch[0]) : null;
    switch (tableHeadName.trim()) {
        case 'TP trades':
            tableData.style.color = 'green';
            break;
        case 'Start balance':
            startBalance = floatValue;
            break;
        case 'SL trades':
            tableData.style.color = 'red';
            break;
        case 'End balance':
            tableData.style.color = startBalance > floatValue ? 'red' : 'green';
            ;
            break;
        case 'PNL':
            // Extract the percentage value from the text
            const percentageMatch = tableData.textContent.match(/-?\d+\.\d+/);
            if (percentageMatch) {
                const percentage = parseFloat(percentageMatch[0]);
                tableData.style.color = percentage < 0 ? 'red' : 'green';
            }
            break;
        // Add more cases as needed
        default:
            // Handle other cases or do nothing
            break;
    }
}

const spinner = document.createElement('span');

function showSpinner(button) {
    spinner.classList.add('spinner-border', 'spinner-border-sm');
    spinner.setAttribute('role', 'status');
    spinner.setAttribute('aria-hidden', 'true');
    // button.innerHTML = '';

    button.appendChild(spinner);
}

function delSpinner(button) {
    button.removeChild(spinner);
}

