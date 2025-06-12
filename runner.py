import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db.models import Prefetch
from chats.models import Conversation
from accounts.models import User
from accounts.enums import UserType

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
