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

function checkMinMaxInputValue(){
    if (parseInt(this.min) <= parseInt(this.value) && parseInt(this.value) <= parseInt(this.max)){
        this.classList.remove('errorMsg');
        deleteHelpText(this.parentElement);
    }
    else{
        if(this.placeholder.includes('min')){
            pastHelpText(this.parentElement, errMsg=this.placeholder)
        }
        this.classList.add('errorMsg');
        this.animate(errInputAnimation.keyframe, errInputAnimation.options);;
    }
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