document.addEventListener('DOMContentLoaded', function() {
    const bookingForm = document.getElementById('bookingForm');

    if (bookingForm) {
        // Set minimum date to tomorrow in user's timezone
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(0, 0, 0, 0);
        const minDate = tomorrow.toISOString().split('T')[0];
        document.getElementById('bookingDate').min = minDate;

        bookingForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const courtName = document.getElementById('courtName').value;
            const bookingDate = document.getElementById('bookingDate').value;
            const bookingTime = document.getElementById('bookingTime').value;

            // Create dates for comparison
            const selectedDateTime = new Date(`${bookingDate}T${bookingTime}`);
            const now = new Date();

            // Set both dates to start of day for comparison
            const selectedDate = new Date(selectedDateTime);
            selectedDate.setHours(0, 0, 0, 0);

            const today = new Date(now);
            today.setHours(0, 0, 0, 0);

            if (selectedDate <= today) {
                alert('Please select a future date for booking');
                return;
            }

            try {
                const response = await fetch('/schedule-booking', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        court_name: courtName,
                        booking_time: selectedDateTime.toISOString()
                    })
                });

                const data = await response.json();

                if (data.status === 'success') {
                    notificationManager.sendNotification(
                        'Booking Scheduled',
                        `Booking scheduled for ${courtName} at ${bookingTime} on ${bookingDate}`
                    );

                    // Reset form
                    bookingForm.reset();
                } else {
                    alert('Error scheduling booking: ' + data.message);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error scheduling booking');
            }
        });
    }
});