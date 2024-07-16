const SYMBOL_INFO_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr";
const TABLE_BODY = document.querySelector("#tableBodySymbolInfo");
const TABLE = document.querySelector("#tableSymbolInfo");
const TABLE_HEADS = Array.from(TABLE.querySelectorAll("th"));

// const strategySelectionBtns = document.querySelectorAll('.strategy-selection button');


let tableInputValue = null;
let choosedSymbol = null;


async function getSymbolInfo() {
    try {
        const response = await fetch(SYMBOL_INFO_URL);

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        let desiredPairs;
        // # 314-DB2Range
        try {
            const response = await fetch('/get_assets_list/');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const pairs = await response.json();
            desiredPairs = pairs.dexima_symbols_list;
            console.log(desiredPairs)

        } catch (error) {
            console.error('There was a problem with the fetch operation:', error);
        }

        // Фильтрация данных, чтобы оставить только нужные пары

        const filteredPairs = data.filter(pair => desiredPairs.includes(pair.symbol));

        return filteredPairs;
    } catch (error) {
        console.error('Error in getDesiredPairs:', error.message);
        throw error; // Повторное генерирование ошибки для ее передачи
    }
}


async function fillTable() {

    const symbolDataArray = await getSymbolInfo();
    console.log(symbolDataArray)
    TABLE_BODY.innerHTML = "";
    await symbolDataArray.forEach(async function (symbolData, num) {
        let newTR = await createTableRow(symbolData, num);
        newTR.addEventListener('click', function (e) {
            symbolClickAction.call(this, e)
        });
        TABLE_BODY.insertAdjacentElement("beforeend", newTR);
    });


    // sort by previous choice
    TABLE_HEADS.forEach(function (th, index) {
        if (th.classList.contains("desc") || th.classList.contains("asc")) {
            let rows = Array.from(TABLE_BODY.querySelectorAll("tr"));
            rows.sort(comparator(index));
            if (th.classList.contains("desc")) {
                rows = rows.reverse();
            }
            rows.forEach(function (row) {
                TABLE_BODY.appendChild(row);
            });
        }
    });
}

async function createTableRow(symbolInfo, num) {

    const newTR = document.createElement("tr");
    let symbolText = symbolInfo.symbol.toLowerCase();
    if (!symbolText.startsWith(tableInputValue) && tableInputValue) {
        newTR.style.display = "none";
    }

    const TdSymbol = document.createElement("td");
    const TdPrice = document.createElement("td");
    const TdPriceChange = document.createElement("td");
    const TdVolume = document.createElement("td");

    TdSymbol.innerHTML = symbolInfo.symbol;
    TdPrice.innerHTML = symbolInfo.lastPrice;
    TdPriceChange.innerHTML = symbolInfo.priceChangePercent;
    let colorToChangePriceTd = parseFloat(symbolInfo.priceChangePercent) > 0 ? 'green' : 'red';

    TdPriceChange.style.color = colorToChangePriceTd;
    TdVolume.innerHTML = parseFloat(symbolInfo.volume).toLocaleString('en-US');
    const TdArray = [TdSymbol, TdPrice, TdPriceChange, TdVolume];

    TdArray.forEach(function (td) {
        newTR.insertAdjacentElement("beforeend", td);
    });

    // TdSymbol.addEventListener('click', (el) => symbolClickAction(el))
    return newTR
}

async function addTableHeadSort() {

    TABLE_HEADS.forEach(function (th, index) {
        th.addEventListener("click", function () {

            let rows = Array.from(TABLE_BODY.querySelectorAll("tr"));
            rows.sort(comparator(index));

            this.asc = !this.asc;
            if (!this.asc) {
                rows = rows.reverse();
            }

            rows.forEach(function (row) {
                TABLE_BODY.appendChild(row);
            });

            // Видалити всі класи сортування і додати потрібний для позначення напрямку
            TABLE_HEADS.forEach(function (otherTh) {
                otherTh.classList.remove("asc", "desc");
            });
            th.classList.add(this.asc ? 'asc' : 'desc');

        });
        // Додати стрілки сортування за замовчуванням
        th.innerHTML += '<span class="asc" style="cursor: pointer;"> ↑</span><span class="desc" style="cursor: pointer;">↓</span>';
        th.classList.add("default-sort");
    });
}


function comparator(index) {
    return function (a, b) {

        var valA = transToInteger(getCellValue(a, index));
        var valB = transToInteger(getCellValue(b, index));

        // Перевірити, якщо значення рівні, порівняти за іншими стовпцями
        if (valA === valB) {
            for (var i = 0; i < TABLE_HEADS.length; i++) {
                if (i !== index) {
                    valA = getCellValue(a, i);
                    valB = getCellValue(b, i);
                    if (valA !== valB) {
                        break;
                    }
                }
            }
        }

        return !isNaN(valA) && !isNaN(valB) ?
            valA - valB :
            valA.toString().localeCompare(valB);
    };
}

function getCellValue(row, index) {
    return row.children[index].textContent;
}

function transToInteger(val) {
    var endsWithDollarOrPercent = /[$%]/.test(val);
    if (endsWithDollarOrPercent) {
        return parseFloat(val.replace(/[$%]/g, ''));
    } else {
        return val;
    }
}


(async () => {
    await fillTable();
    await addTableHeadSort();
})();


function fillTableWrapper() {
    fillTable().catch(error => {
        console.error('Error in fillTable:', error.message);
    });
}

function symbolClickAction(e) {
    // TODO HERE AN ERROR 
    if (!this.contains(e.target) || e.target === null) return


    // el.target.parentElement.style.backgroundColor = "black"
    strategyButtons.forEach((btn) => btn.disabled = false);
    let trSymbol = this.querySelector('td').textContent.toLocaleLowerCase()
    if (choosedSymbol) {
        makeRowsVisible();
        choosedSymbol = null;
        document.querySelector('.fourhSection').classList.add('hidden1')
    } else {
        choosedSymbol = this.querySelector('td');
        filterSymbolTableBySymbol();
        // show next section 
        document.querySelector('.fourhSection').classList.remove('hidden1')
    }

    tableInputValue = trSymbol;
}

// TODO uncomment this for update symbols table
// setInterval(fillTableWrapper, 60000);