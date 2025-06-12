import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db.models import Prefetch, F
from chats.models import Conversation
from accounts.models import User, BusinessUser
from accounts.enums import UserType, BusinessUserRoleType

conversation_objs = list()
conversations = Conversation.objects.prefetch_related(
    Prefetch("users", queryset=User.objects.filter(type=UserType.TALENT))
).iterator(chunk_size=100)
for conversation in conversations:
    if conversation.users.count() == 2:
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

print("update business owners")
