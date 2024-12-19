


tasks = [
        {
            "name": "Delete Old Notifications - 5 AM",
            "func": "notification.tasks.delete_notifications_older_than_a_month",
            "cron": "0 5 * * *",  # Every day at 5:00 AM
        }
    ]
