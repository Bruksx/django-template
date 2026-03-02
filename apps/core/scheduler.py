
tasks = [
        {
            "name": "Delete Old Exports - 3 AM",
            "func": "core.tasks.delete_old_exports",
            "cron": "0 3 * * *",  # Every day at 3:00 AM
        },

    ]
