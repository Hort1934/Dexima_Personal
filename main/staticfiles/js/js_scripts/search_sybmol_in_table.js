const tableBodySymbolInfo = document.querySelector("#tableBodySymbolInfo");
const searchSymbolInput = document.querySelector("#search-input");

searchSymbolInput.addEventListener('input', function(e) {
    tableInputValue = e.target.value.toLowerCase();
    filterSymbolTableBySymbol();
});

function filterSymbolTableBySymbol() {
    let tableRows = tableBodySymbolInfo.querySelectorAll('tr');

    tableRows.forEach(function(row) {
        let symbolText = row.children[0].textContent.toLowerCase();
        if (choosedSymbol) {
            if (choosedSymbol.parentElement == row) {
                row.style.display = "table-row";
            } else {
                row.style.display = "none";
            }
        } else {
            if (tableInputValue === null || tableInputValue == "") {
                row.style.display = "table-row";
            } else {
                if (symbolText.includes(tableInputValue)) {
                    row.style.display = "table-row";
                } else {
                    row.style.display = "none";
                }
            }
        }
    });
}

function makeRowsVisible() {
    let tableRows = tableBodySymbolInfo.querySelectorAll('tr');
    tableRows.forEach(function(row) {
        row.style.display = "table-row";
    });
}
