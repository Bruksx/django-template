


def bulk_delete_notifications_service(notifications, user):
    for notification in notifications.iterator():
        notification.delete_notification(user)
    return

def bulk_read_notifications_service(notifications, user):
    for notification in notifications.iterator():
        notification.view(user)
    return