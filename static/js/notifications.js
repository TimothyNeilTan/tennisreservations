class NotificationManager {
    constructor() {
        this.checkPermission();
    }

    checkPermission() {
        if (!("Notification" in window)) {
            console.log("This browser does not support notifications");
            return;
        }

        if (Notification.permission !== "granted") {
            Notification.requestPermission();
        }
    }

    sendNotification(title, message) {
        if (Notification.permission === "granted") {
            new Notification(title, {
                body: message,
                icon: "https://cdn.jsdelivr.net/npm/feather-icons/dist/icons/calendar.svg"
            });
        }
    }
}

const notificationManager = new NotificationManager();
