async function getMinimalQuantity(symbol){
    console.log('here')
    let url;
    if(exchange.value == "Binance"){
        url = `/get_minimal_quantity/${symbol}/`;
    }else{
        url = `/get_bybit_open_order_rules/?symbol=${symbol.toLocaleLowerCase()}`;
    }
    return fetching_data(url);
    };



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
}