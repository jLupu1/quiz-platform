document.addEventListener("DOMContentLoaded", function() {
    const deadlineData = document.getElementById('quiz-deadline').textContent;
    const startData = document.getElementById('quiz-start').textContent;
    const deadline = new Date(JSON.parse(deadlineData)).getTime();
    const start = new Date(JSON.parse(startData)).getTime();

    const original_distance =  deadline-start


    const timerDisplay = document.getElementById("quiz-timer");

    const progressBar = document.getElementById('progress-bar')

    const timerInterval = setInterval(function() {
        const now = new Date().getTime();
        const distance_now = deadline - now;
        const percentage = (distance_now /original_distance) * 100


        //  time is up
        if (distance_now <= 0) {
            clearInterval(timerInterval);
            timerDisplay.innerHTML = '<i class="bi bi-clock me-2 fs-3 text-danger"></i> <span class="text-danger">00:00</span>';
            timerDisplay.classList.add('flash-animation');

            alert("Time is up! Your quiz is being automatically submitted.");

            const submitForm = document.getElementById('auto-submit-form');
            if (submitForm) {
                submitForm.submit();
            }
            return;
        }

        // calculate minutes and seconds
        const minutes = Math.floor((distance_now % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance_now % (1000 * 60)) / 1000);

        // add leading zeros
        const formattedMinutes = minutes < 10 ? "0" + minutes : minutes;
        const formattedSeconds = seconds < 10 ? "0" + seconds : seconds;

        timerDisplay.innerHTML = `<i class="bi bi-clock me-2 fs-3"></i> ${formattedMinutes}:${formattedSeconds}`;

        console.log(percentage)

        progressBar.style.width = `${percentage}%`;

        progressBar.setAttribute('aria-valuenow', toString(percentage));

        if (percentage < 25) {
            progressBar.classList.remove('bg-success');
            progressBar.classList.add('bg-danger');
        } else {
            // Keep it green if it is above 25%
            progressBar.classList.remove('bg-danger');
            progressBar.classList.add('bg-success');
        }

    }, 1000);
});