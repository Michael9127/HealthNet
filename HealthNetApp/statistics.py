from django.db.models import Count, Avg
from .models import Appointment, Prescription, LogEntry
from itertools import groupby
import math
from collections import Counter
from django.http import Http404

def getAppointments(start, end):
    try:
        return Appointment.objects.filter(start__gte=start, end__lte=end)
    except:
        raise Exception("Couldnt fetch Appointments")

def prescriptionStats(start, end):
    prescriptions = Prescription.objects.values_list('name')

    #ToDo: Needs to be start date once model is updated
    # Filters all prescription within date range, and aggregates a count of every unique prescription.
    return prescriptions.filter(start_Date__gte=start,start_Date__lte=end).annotate(count=Count('name')).order_by('-count')

def patientAppointmentStats(start, end):
    return getAppointments(start,end).values_list('patient__name').annotate(count=Count('patient')).order_by('-count')

def patientAppointmentLengthStats(start, end):
    appointments = getAppointments(start, end).order_by('patient__name').values_list('patient__name', 'end', 'start').order_by('patient__name')
    avgApptLength = []

    # Groups every appointment by unique patient, and returns an iterator for each patient's appointments (apps)
    for patient, appt in groupby(appointments, lambda x: x[0]):
        counter = 0
        sum = 0

        # Iterates iterator and calculates average for each patient
        for duration in appt:
            counter += 1

            # Calculates the duration of each appointment (end time - start time) and adds to running total
            sum += (duration[1]-duration[2]).seconds/60

        # Each patient's average is saved in a 2D array
        avgApptLength.append([patient, str(int(sum/counter))+' Minutes'])
    return avgApptLength


def hospitalAppointmentStats(start, end):
    # Filters appointments by date, aggregates amount of appointments for each unique patient, and averages those counts
    return getAppointments(start,end).values_list('patient__name').annotate(count=Count('patient')).aggregate(average=Avg('count'))['average']

def hospitalAppointmentLengthStats(start, end):
    appointmentTimes = getAppointments(start,end).values_list('end', 'start')
    if len(appointmentTimes) > 0:
        # Calculates duration of each appointment within date range and appends to list
        durations = [(times[0]-times[1]).seconds/60 for times in appointmentTimes]
        # ToDo: math.fsum because sum wont work???
        # Calculates average duration
        return str(math.fsum(durations)/len(durations)) + ' Minutes'
    return '0 Minutes'

def hospitalAdmissionReasons(start, end):
    logs = LogEntry.objects.filter(time__gte=start, time__lte=end, action_type='u', thing_type='p', thing_field='admitted_to', eventDescription__icontains='reason').values_list('eventDescription', flat=True)
    AdmissionReasons = []
    temp =list(Counter(logs).items())
    for reason in list(Counter(logs).items()):
        index = reason[0].find('reason')+8
        AdmissionReasons.append([reason[0][index:-1], reason[1]])
    return AdmissionReasons

