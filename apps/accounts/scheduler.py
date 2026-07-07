tasks = [
    {
        "name": "Incomplete Profile Remainder - Everyday",
        "func": "accounts.tasks.remind_incomplete_profiles_task",
        "cron": "0 0 * * 1,4" # Every day at 12 am on monday and thursday
    },
    {
        "name": "Weekly Profile Completion Report - Every Monday",
        "func": "accounts.tasks.send_weekly_report_of_candidates",
        "cron": "0 8 * * 1" # Every week at 8 am on monday morning
    },
    {
        "name": "Talent Profile Source Weekly Report - Every Monday",
        "func": "accounts.tasks.send_weekly_report_of_talent_sources",
        "cron": "0 9 * * 1" # Every week at 9 am on monday morning
    }
]