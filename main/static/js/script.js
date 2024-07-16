const defaultSelect = () => {
    const element = document.querySelector('.default');
    const choices = new Choices(element, {
        searchEnabled: true,
        allowHTML: true,
    });
};

defaultSelect();

document.addEventListener('DOMContentLoaded', () => {
    const element = document.querySelector('.default');
    const choices = new Choices(element, {
        searchEnabled: true,
        allowHTML: true,
    });

    element.addEventListener('input', () => {
        const selectedValue = element.value; // Получите значение, введенное в поле поиска

        // Используйте метод setChoiceByValue() для выбора элемента, соответствующего введенному значению
        choices.setChoiceByValue(selectedValue);
    });
});
