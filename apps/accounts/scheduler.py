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
        "name": "Deactivate Inactive Talent Profile",
        "func": "accounts.tasks.deactivate_inactive_talents",
        "cron": "0 2 * * *" # Every day at 2 am
    },
    {
        "name": "Deactivate Incomplete Talent Profile",
        "func": "accounts.tasks.deactivate_incomplete_talent_account",
        "cron": "0 3 * * *" # Every day at 3 am
    },
    {
        "name": "Deactivate Incomplete Talent Profile - 7",
        "func": "accounts.tasks.deactivation_reminder_incomplete_talent_accounts",
        "kwargs": "days=7",
        "cron": "0 7 * * *" # Every day at 7 am
    },
{
        "name": "Deactivate Incomplete Talent Profile - 1",
        "func": "accounts.tasks.deactivation_reminder_incomplete_talent_accounts",
        "kwargs": "days=1",
        "cron": "0 6 * * *" # Every day at 6 am
    },

    {
        "name": "Deactivate Inactive Talent Profile - 7",
        "func": "accounts.tasks.deactivation_reminder_inactive_talent_accounts",
        "kwargs": "days=7",
        "cron": "0 5 * * *" # Every day at 5 am
    },
{
        "name": "Deactivate Inactive Talent Profile - 15",
        "func": "accounts.tasks.deactivation_reminder_inactive_talent_accounts",
        "kwargs": "days=15",
        "cron": "0 4 * * *" # Every day at 4 am
    }

]