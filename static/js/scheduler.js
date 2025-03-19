document.addEventListener('DOMContentLoaded', function() {
    const bookingForm = document.getElementById('bookingForm');
    const courtNameSelect = document.getElementById('courtName');
    const bookingDateInput = document.getElementById('bookingDate');
    const bookingTimeSelect = document.getElementById('bookingTime');

    if (bookingForm) {
        // Set minimum date to tomorrow in user's timezone
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(0, 0, 0, 0);
        const minDate = tomorrow.toISOString().split('T')[0];
        bookingDateInput.min = minDate;

        // Function to check if we can load times
        function updateTimeSelectState() {
            const courtName = courtNameSelect.value;
            const bookingDate = bookingDateInput.value;
            
            if (!courtName || !bookingDate) {
                bookingTimeSelect.disabled = true;
                // Clear existing options
                while (bookingTimeSelect.options.length > 0) {
                    bookingTimeSelect.remove(0);
                }
                // Add appropriate placeholder based on what's missing
                const placeholderOption = document.createElement('option');
                placeholderOption.value = "";
                if (!courtName && !bookingDate) {
                    placeholderOption.text = "Select a court and booking date first";
                } else if (!courtName) {
                    placeholderOption.text = "Select a court first";
                } else {
                    placeholderOption.text = "Select a booking date first";
                }
                bookingTimeSelect.add(placeholderOption);
                
                // Remove any existing note
                const noteDiv = document.getElementById('timeNote');
                if (noteDiv) noteDiv.remove();
            } else {
                loadTimeOptions();
            }
        }

        // Function to load time options based on court and date
        async function loadTimeOptions() {
            const courtName = courtNameSelect.value;
            const bookingDate = bookingDateInput.value;
            
            if (!courtName || !bookingDate) {
                return; // Don't proceed if either value is missing
            }
            
            bookingTimeSelect.disabled = true;
            
            // Clear existing options
            while (bookingTimeSelect.options.length > 0) {
                bookingTimeSelect.remove(0);
            }
            
            // Add loading option
            const loadingOption = document.createElement('option');
            loadingOption.text = 'Loading available times...';
            loadingOption.disabled = true;
            bookingTimeSelect.add(loadingOption);
            
            try {
                const response = await fetch('/get-available-times', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        court_name: courtName,
                        date: bookingDate
                    })
                });
                
                const data = await response.json();
                
                // Clear loading option
                while (bookingTimeSelect.options.length > 0) {
                    bookingTimeSelect.remove(0);
                }
                
                if (data.status === 'success') {
                    // Add placeholder option
                    const placeholderOption = document.createElement('option');
                    placeholderOption.value = "";
                    placeholderOption.text = "Select a time";
                    bookingTimeSelect.add(placeholderOption);
                    
                    // Add time options
                    data.times.forEach(time => {
                        const option = document.createElement('option');
                        option.value = time;
                        
                        // Format display time (convert 24h to 12h format)
                        const [hours, minutes] = time.split(':');
                        const hour = parseInt(hours);
                        const ampm = hour >= 12 ? 'PM' : 'AM';
                        const displayHour = hour > 12 ? hour - 12 : (hour === 0 ? 12 : hour);
                        option.text = `${displayHour}:${minutes} ${ampm}`;
                        
                        bookingTimeSelect.add(option);
                    });
                    
                    // Enable the select
                    bookingTimeSelect.disabled = false;
                    
                    // Add a note if times were scraped
                    if (data.is_scraped) {
                        const noteDiv = document.getElementById('timeNote') || document.createElement('div');
                        noteDiv.id = 'timeNote';
                        noteDiv.className = 'text-info small mt-1';
                        noteDiv.textContent = 'These are actual available times from the booking system.';
                        bookingTimeSelect.parentNode.appendChild(noteDiv);
                    } else {
                        // Remove the note if it exists
                        const noteDiv = document.getElementById('timeNote');
                        if (noteDiv) noteDiv.remove();
                    }
                } else {
                    // Add error option
                    const errorOption = document.createElement('option');
                    errorOption.text = 'Error loading times';
                    errorOption.disabled = true;
                    bookingTimeSelect.add(errorOption);
                }
            } catch (error) {
                console.error('Error loading times:', error);
                // Add error option
                const errorOption = document.createElement('option');
                errorOption.text = 'Error loading times';
                errorOption.disabled = true;
                bookingTimeSelect.add(errorOption);
            }
        }
        
        // Add event listeners to court and date inputs
        courtNameSelect.addEventListener('change', updateTimeSelectState);
        bookingDateInput.addEventListener('change', updateTimeSelectState);

        // Initial state setup
        updateTimeSelectState();

        bookingForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const courtName = courtNameSelect.value;
            const bookingDate = bookingDateInput.value;
            const bookingTime = bookingTimeSelect.value;

            if (!courtName || !bookingDate || !bookingTime) {
                alert('Please fill in all required fields');
                return;
            }

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
                        'Booking Submitted',
                        `Booking attempt for ${courtName} at ${bookingTime} on ${bookingDate} was ${data.message}`
                    );
                    bookingForm.reset();
                    updateTimeSelectState(); // Reset time select state after form reset
                } else {
                    alert('Booking failed: ' + data.message);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error submitting booking');
            }
        });
    }
});
