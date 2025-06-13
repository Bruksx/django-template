import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db.models import F
from chats.models import Conversation
from accounts.models import User, BusinessUser, Business
from accounts.enums import UserType, BusinessUserRoleType

conversation_objs = list()
conversations = Conversation.objects.iterator()
for conversation in conversations:
    if conversation.users.filter(type=UserType.TALENT.value).count() == 2:
        conversation.locked = True
        conversation_objs.append(conversation)

Conversation.objects.bulk_update(conversation_objs, ["locked"])
print(f"{len(conversation_objs)} conversations locked")


business_user_owners = BusinessUser.objects.filter(business__created_by=F('user')).update(
    role=BusinessUserRoleType.OWNER.value
)
other_staffs = BusinessUser.objects.exclude(business__created_by=F('user')).filter(
    role=BusinessUserRoleType.OWNER.value
).update(role=BusinessUserRoleType.ADMIN.value)

businesses = Business.objects.filter(created_by__isnull=True).iterator()
for business in businesses:
    business_user = BusinessUser.objects.filter(business=business).first()
    business.created_by = business_user.user
    business.save()
    business_user.role = BusinessUserRoleType.OWNER.value
    business_user.save()

print("update business owners")
