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

            // Create dates in user's timezone for comparison
            const selectedDate = new Date(bookingDate);
            const today = new Date();

            // Reset time parts for date comparison
            selectedDate.setHours(0, 0, 0, 0);
            today.setHours(0, 0, 0, 0);

            // Calculate tomorrow for validation
            const tomorrow = new Date(today);
            tomorrow.setDate(today.getDate() + 1);

            if (selectedDate < tomorrow) {
                alert('Please select tomorrow or a future date for booking');
                return;
            }

            // Combine date and time for the booking
            const bookingDateTime = new Date(bookingDate + 'T' + bookingTime);

            try {
                const response = await fetch('/schedule-booking', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        court_name: courtName,
                        booking_time: bookingDateTime.toISOString()
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