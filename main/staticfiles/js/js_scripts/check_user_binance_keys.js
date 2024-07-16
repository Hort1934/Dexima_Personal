const connectUrl = document.querySelector("#connectUrlBinance");
const connectUrlBybit = document.querySelector("#connectUrlBybit");
let ApiKeyIsconnected = false;


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

async function checkConnection() {
    const res = await fetching_data("/check_user_api_keys");
    if (res['keys_saved']) {
        connectUrl.style.color = "green";
        connectUrl.innerHTML = "CONNECTED";
        ApiKeyIsconnected = true;
    }
}

async function checkConnectionBybit() {
    const res = await fetching_data("/check_user_api_keys_bybit");
    if (res['keys_saved']) {
        connectUrlBybit.style.color = "green";
        connectUrlBybit.innerHTML = "CONNECTED";
        ApiKeyIsconnected = true;
    }
}

checkConnection();
checkConnectionBybit();