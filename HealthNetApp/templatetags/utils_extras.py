#http://stackoverflow.com/questions/4577513/how-do-i-change-a-django-template-based-on-the-users-group
from django import template
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from HealthNetApp.models import Person
from django.utils import timezone

register = template.Library()
@register.filter(name='has_group')
def has_group(user, group_name):
    try:
        group = Group.objects.get(name=group_name)
    except:
        return False  # group doesn't exist, so for sure the user isn't part of the group

    # for superuser or staff, always return True
    if user.is_superuser or user.is_staff:
        return True

    return user.groups.filter(name=group_name).exists()

@register.filter(name='new_message')
def new_message(user):
    person = get_object_or_404(Person, username=user.username)
    return person.get_messages().filter(read=False).count()
    
@register.filter(name='in_past')
def in_past(time):
    return int(time < timezone.now())