tasks = [
    {
        "name": "Incomplete Profile Remainder - Everyday",
        "func": "accounts.tasks.remind_incomplete_profiles_task",
        "cron": "0 0 * * 1,4" # Every day at 12 am on monday and thursday
    }
]