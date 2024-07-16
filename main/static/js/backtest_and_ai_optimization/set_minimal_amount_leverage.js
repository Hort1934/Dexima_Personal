const errInputAnimation = {
    keyframe: 
        [
            { transform: 'translateX(0)' },
            { transform: 'translateX(-2px)' }, // Измените значение влево
            { transform: 'translateX(2px)' }   // Измените значение вправо
        ],
    options: {
        duration: 100,  // Продолжительность анимации в миллисекундах
        iterations: 3   // Количество повторений (в данном случае, дважды)
    }
}

const errTextAnimation = {
    keyframe: 
        [
            { height: '0', opacity: '0.5' },
            { height: 'auto', opacity: '1' } // Измените значение вправо
        ],
    options: {
        duration: 500,  // Продолжительность анимации в миллисекундах
        easing: 'ease-in-out'  // Тип анимации (в данном случае, плавное ускорение и замедление)
    }
}

async function getMinimalQuantity(symbol){
    let url;
    console.log(124325)
    if(exchange.value.toLowerCase() == "binance"){
        url = `/get_minimal_quantity/${symbol}/`;
    }else if(exchange.value.toLowerCase() == "bybit"){
        url = `/get_bybit_open_order_rules/?symbol=${symbol.toLocaleLowerCase()}`;
    }
    
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

function checkMinMaxInputValue(){
    if (parseFloat(this.min) <= parseFloat(this.value) && parseFloat(this.value) <= parseFloat(this.max)){
        this.classList.remove('errorMsg');
        deleteHelpText(this.parentElement);
        checkDashboardBtnAvailability(); // Add a button availability check upon successful validation
    }
    else{
        if(this.placeholder.includes('min')){
            pastHelpText(this.parentElement, this.placeholder);
        }
        this.classList.add('errorMsg');
        this.animate(errInputAnimation.keyframe, errInputAnimation.options);
        disableDashboardBtn(); // Add button deactivation when an error is detected
    }
}

function checkDashboardBtnAvailability() {
    if (!total_investment.classList.contains('errorMsg') && !leverage.classList.contains('errorMsg')) {
        dashbordBtn.disabled = false; // Enable the button if both fields are validated
    }
}

function disableDashboardBtn() {
    dashbordBtn.disabled = true; // Turn off the button when an error is detected in the total_investment or leverage fields
}


function pastHelpText(parentElement, errMsg="Test txt"){
    if (parentElement.contains(parentElement.querySelector('.errMsgTxt')))
        return;
    const div = document.createElement('div');
    div.textContent = errMsg;
    div.classList.add('errMsgTxt')
    parentElement.insertAdjacentElement('beforeend', div)
    // Анимация на плавное расширение элемента
    let animation = div.animate(errTextAnimation.keyframe, errTextAnimation.options);

    animation.addEventListener('finish', function(){
        div.style.height = 'auto';
    })
}

function deleteHelpText(parentElement){
    let errMsgElement = parentElement.querySelector('.errMsgTxt');
    if (errMsgElement){
        errMsgElement.remove()
    }
}