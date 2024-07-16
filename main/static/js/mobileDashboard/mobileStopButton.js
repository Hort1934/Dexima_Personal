
// [stop buttons func]
async function handleStopButtonClick(itemId) {
    document.getElementById('dialogOverlay').style.display = 'block';
    document.getElementById('simpleDialog').style.display = 'block';
    document.getElementById('botId').innerText = itemId;

    const closeButton = document.querySelector('.closeButton');

    if (!closeButton.hasEventListener) {
        closeButton.addEventListener('click', function() {
            console.log("Close button clicked!");
            document.getElementById('simpleDialog').style.display = 'none';
            document.getElementById('dialogOverlay').style.display = 'none';
            document.getElementById('botId').innerText = '';
            document.getElementById('leaveOpenCheckbox').checked = false;
            document.getElementById('closeMarketCheckbox').checked = false;
        });
        closeButton.hasEventListener = true;
    } else {
        console.error("Element with class 'close' not found.");
    }

    let confirmButton = document.querySelector('.dialog-button');
    if (confirmButton) {
        // Removing the previous event handler if one was added previously
        if (confirmButton.clickHandler) {
            confirmButton.removeEventListener('click', confirmButton.clickHandler);
        }

        // Adding a new event handler
        confirmButton.clickHandler = async () => {
            if (!document.getElementById('leaveOpenCheckbox').checked && !document.getElementById('closeMarketCheckbox').checked) {
                alert("Please select at least one option.");
                return;
            }

            await confirmShutdown(itemId);
            let tableToRemove = document.querySelector(`table[data-item-id="${itemId}"]`);
            if (tableToRemove) {
                tableToRemove.remove();
            }
        };

        confirmButton.addEventListener('click', confirmButton.clickHandler);
    } else {
        console.error("Element with class 'dialog-button' not found.");
    }

    setTimeout(() => {
        let remainingTables = document.querySelectorAll('table');
        if (remainingTables.length === 0) {
            window.location.reload();
        }
    }, 15000);
}


// The second function takes itemId and is executed after confirmation
function confirmShutdown(itemId) {
    let leaveOpenCheckbox = document.getElementById('leaveOpenCheckbox');
    let closeMarketCheckbox = document.getElementById('closeMarketCheckbox');

    // Leave positions and orders open
    if (leaveOpenCheckbox.checked) {
        try {
            const response = fetch(`/dashboard_stop/${itemId}/`);
            console.log(response);
        } catch (error) {
            console.error('Error:', error);
        }
    }

    // Close positions and orders at the market price
    if (closeMarketCheckbox.checked) {
        try {
            const response = fetch(`/dashboard_stop_and_close/${itemId}/`);
            console.log(response);
        } catch (error) {
            console.error('Error:', error);
        }
    }

    // Resetting checkboxes
    leaveOpenCheckbox.checked = false;
    closeMarketCheckbox.checked = false;

    document.getElementById('simpleDialog').style.display = 'none';
    document.getElementById('dialogOverlay').style.display = 'none';
}
