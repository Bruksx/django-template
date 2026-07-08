import sys

from django_q.tasks import async_task as django_async_task


def async_task(func, *args, **kwargs):
    if "test" in sys.argv:
        """ to enable it run synchronously in tests """
        return func(*args, **kwargs)
    return django_async_task(func, *args, **kwargs)


def schedule_cron_tasks(tasks):
    get_task_name = lambda task: f'Schedule: {task["name"]}'
    from django_q.models import Schedule
    task_names = [get_task_name(task) for task in tasks]
    for task in tasks:
        task_name = get_task_name(task)
        if Schedule.objects.filter(name=task_name).exists():
            continue
        Schedule.objects.create(
            name=task_name,
            func=task["func"],
            kwargs=task.get("kwargs"),
            schedule_type=Schedule.CRON,
            cron=task["cron"],
            repeats=-1,  # Repeat indefinitely
        )
    Schedule.objects.exclude(name__in=task_names).filter(name__startswith="Schedule:").delete()

    print("Cron tasks scheduled successfully.")