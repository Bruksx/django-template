
tasks = [
        {
            "name": "Delete Old Exports - 3 AM",
            "func": "core.tasks.delete_old_exports",
            "cron": "0 3 * * *",  # Every day at 3:00 AM
        },
        {
            "name": "Aggregate API Metrics - Every Day",
            "func": "core.tasks.aggregate_page_metrics",
            "cron": "0 0,4,8,12,16,20 * * *" # Every 4 hours
        },
        {
            "name": "Weekly Profile Completion Report - Every Monday",
            "func": "core.tasks.aggregate_api_metrics",
            "cron": "5 0 * * *" # Every day at 00:05 daily
        }
]