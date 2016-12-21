from .models import LogEntry, Person
from django.db import models

import datetime
from django.utils.timezone import make_aware, get_default_timezone
#from django.db import models.DoesNotExist

def log_event(username, action_type, thing_type,
	thing_instance, thing_field, eventDescription):

	#verify that all arguments are valid

#IF NO PERSON OBJECT WITH SPECIFIED USERNAME EXISTS
#	if(Person.objects.get(username=username) == []):
#INVALID USERNAME
#		print("Invalid username given to logger")

	#if the action type specified is not one of the available action types
#	if !any(action_type in action for action in LogEntry.log_types):
#INVALID ACTION TYPE
#		print("Invalid action type given to logger")

#TO CHECK thing_type AND thing_instance, thing_type WOULD HAVE TO BE AN ENUM
	#OF THE POSSIBLE MODELS/OBJECTS THAT CAN HAVE THEIR FIELDS MODIFIED, AND
	#WE WOULD HAVE TO CHECK IF THERE WAS AN INSTANCE OF THE SPECIFIED OBJECT
	#TYPE WITH THE SPECIFIED pkid/thing_instance

#IN ORDER TO CHECK thing_field, WE WOULD PROBABLY HAVE TO HAVE AN ENUM FOR
	#EACH MODEL/OBJECT, LISTING ITS ATTRIBUTES, THEN CHECK THAT THE SPECIFIED
	#ATTRIBUTE EXISTS FOR THE SPECIFIED MODEL/OBJECT

	#create a new log entry with arguments
	new_entry = LogEntry(user=Person.objects.get(username=username),
					time=make_aware(datetime.datetime.now(), get_default_timezone()),
					action_type=action_type, thing_type=thing_type,
					thing_instance=thing_instance, thing_field=thing_field,
					eventDescription=eventDescription)

#	new_entry = LogEntry(Person.objects.get(username=username), action_type, thing_type, thing_instance, thing_field, eventDescription)

	new_entry.save()


def view_log_entries_by_username(username):
	try:
		return LogEntry.objects.filter(user=Person.objects.get(username=username))
	except Person.DoesNotExist:
		return []


def view_log_entries_by_type(action_type):
	return LogEntry.objects.filter(action_type=action_type)
