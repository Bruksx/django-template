tasks = [
    {
        "name": "Aggregate Page Metrics - Every 4 Hours",
        "func": "core.tasks.aggregate_page_metrics",
        "cron": "0 0,4,8,12,16,20 * * *"
    },
    {
        "name": "Aggregate API Metrics - Every Day at 00:05",
        "func": "core.tasks.aggregate_api_metrics",
        "cron": "5 0 * * *"
    }
]