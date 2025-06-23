
tasks = [
        {
            "name": "Job Application Notification - 5 AM",
            "func": "jobs.tasks.share_job_application_notification_task",
            "cron": "0 5 * * *",  # Every day at 5:00 AM
        },
        {
            "name": "Job Application Notification - 10 AM",
            "func": "jobs.tasks.job_application_notification_task",
            "cron": "0 10 * * *",  # Every day at 10:00 AM
        },
        {
            "name": "Job Application Notification - 4 PM",
            "func": "jobs.tasks.job_application_notification_task",
            "cron": "0 16 * * *",  # Every day at 4:00 PM
        },
        {
            "name": "Job Sharing Notification - 4 PM",
            "func": "jobs.tasks.job_sharing_notification_task",
            "cron": "0 16 * * *",  # Every day at 4:00 PM
        },
        {
            "name": "Job Performance Notification - Friday 3 PM",
            "func": "jobs.tasks.job_performance_notification_task",
            "cron": "0 15 * * 5",  # Every Friday at 3:00 PM
        },
        {
        "name": "Lever JobPost Download - 1 AM",
        "func": "jobs.tasks.fetch_job_posts_from_lever",
        "cron": "0 1 * * *",  # Every day at 1:00 AM
        }
    ]
