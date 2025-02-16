document.addEventListener('DOMContentLoaded', function() {
    const bookingForm = document.getElementById('bookingForm');
    
    if (bookingForm) {
        bookingForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const courtName = document.getElementById('courtName').value;
            const bookingDate = document.getElementById('bookingDate').value;
            const bookingTime = document.getElementById('bookingTime').value;
            
            // Combine date and time
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
