"""
filename: models.py
authors: Chris Lenter, Coleman Link, Mike Borkenstein, Rich Patulski, Sam Kilgore
purpose: the model classes for the HealthNetApp application
"""

import datetime, re, copy
from django.db import models
from django.db.models import Q
from django.utils import timezone

# ToDo: on_delete fields
# ToDo: docstrings
# ToDo: default and null values
# todo: __str__ on lots of models


class Person(models.Model):
    name = models.CharField(max_length=50)
    date_of_birth = models.DateField('Date of Birth')
    contact_information = models.CharField(max_length=200)
    username = models.CharField(max_length=30)#.lower()

    def __str__(self):
        return self.name

    def get_messages(self):
        return Message.objects.filter(destination=self).order_by('-date')


class MedicalInformation(models.Model):
    #prescription = models.TextField(max_length=500)
    history = models.TextField(max_length=1000)
    def __str__(self):
        return str(self.history)



class Hospital(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Patient(Person):
    preferred_hospital = models.ForeignKey(Hospital)
    admitted_to = models.ForeignKey(Hospital, null = True, default = None, blank = True, related_name='admitted_to')
    insurance_id = models.CharField(max_length=15)
    medical_information = models.ForeignKey(MedicalInformation)
    #tests = models.ForeignKey(MedicalTest)
    # todo: insurance information
    # todo: "linked to another patient if they are already in the system"
    emergency_contact = models.CharField(max_length=200)

    def list_appointments(self):
        return Appointment.objects.filter(patient=self)

    def appointment_title(self, appointment):
        '''
        Get a friendly appointment title for use with the Calendar view.
        Rationale: a patient calendar only shows their own appointments,
        so having their own name in it is unnecessary.
        :param appointment: an Appointment object
        :return: string
        '''
        return appointment.doctor.name

    def can_create_appointment(self):
        # Patients can only create appointments if they have none outstanding
        return not Appointment.objects.filter(patient=self,
                                              start__gt=timezone.now()).exists()

    def __str__(self):
        return self.name


class MedicalProfessional(Person):
    hospital = models.ForeignKey(Hospital)

    def appointment_title(self, appointment):
        '''
        Get a friendly appointment title for use with the Calendar view.
        Rationale: a MedicalProfessional's calendar shows appointments with
        many patients and many doctors, so some clarity in the calendar
        would be nice.
        :param appointment: an Appointment object
        :return: string
        '''
        return appointment.doctor.name + "; " + appointment.patient.name

    def list_patients(self):
        '''
        This is an abstract method, and is not intended to have an
        implementation here. Do not delete it.
        '''
        raise NotImplementedError

    def list_appointments(self):
        '''
        This is an abstract method, and is not intended to have an
        implementation here. Do not delete it.
        '''
        raise NotImplementedError


class Doctor(MedicalProfessional):
    def list_patients(self):
        return Patient.objects.all()

    def list_appointments(self):
        return Appointment.objects.all()


class Nurse(MedicalProfessional):
    def list_patients(self):
        # Nurses can only see patients within their hospital
        # Lazy queryset evaluation prevents this from causing 2 queries, so it is not inefficient
        return Patient.objects.filter(Q(preferred_hospital=self.hospital) | Q(admitted_to=self.hospital))

    def list_appointments(self):
        # Nurses can only see appointments one week in the future
        now = datetime.date.today()
        future = now + datetime.timedelta(days=7)
        # Nurses can only see patients' appointments within their hospital
        return Appointment.objects.filter(end__lt=future,
                                          hospital=self.hospital)


class Administrator(Person):
    def list_appointments(self):
        return Appointment.objects.all()

    def list_patients(self):
        return Patient.objects.all()

    appointment_title = MedicalProfessional.appointment_title


class MedicalTest(models.Model):
    title = models.CharField(max_length=50)
    testDate = models.DateField()
    doctor = models.ForeignKey(Doctor)
    hospital = models.ForeignKey(Hospital)
    results = models.TextField(max_length=1000)
    patient = models.ForeignKey(Patient)
    pending = models.IntegerField(null=True)# 1 means it's confirmed, 0 means pending
    pictures = models.FileField(upload_to='testPics/%Y/%m/%d',default='Uploading a Picture')
    #luckily, django's FileField magically handles when two files have the same path and filename
    pictures1 = models.FileField(upload_to='testPics/%Y/%m/%d',default='Uploading a Second Picture')
    pictures2 = models.FileField(upload_to='testPics/%Y/%m/%d',default='Uploading a Third Picture')
    pictures3 = models.FileField(upload_to='testPics/%Y/%m/%d',default='Uploading a Fourth Picture')
    def dump(self):
        '''
        Returns a string containing all the non-picture fields in this model.
        Purpose: patient export information
        '''
        return "Title: {}\nDate: {}\nDoctor: {}\nHospital: {}\nComments: {}\n".format(
            str(self.title), self.testDate.isoformat(), str(self.doctor), str(self.hospital), str(self.results))

    def __str__(self):
        return self.title + " on " + str(self.testDate)

class Appointment(models.Model):
    start = models.DateTimeField('Appointment Start Time')
    end = models.DateTimeField('Appointment End Time')
    doctor = models.ForeignKey(Doctor)
    hospital = models.ForeignKey(Hospital)
    patient = models.ForeignKey(Patient)

    def conflicts(self, other):
        '''
        Check to see if two appointments are overlapping
        and share a patient or doctor
        :param other: Another instance of Appointment
        :return: boolean
        '''
        if not (self.patient == other.patient or self.doctor == other.doctor):
            return False
        if self.start.date() != other.start.date():
            return False
        if ((other.start <= self.start <= other.end) or
            (other.start <= self.end   <= other.end)):
            return True
        if ((self.start <= other.start <= self.end) or
            (self.start <= other.end   <= self.end)):
            return True
        return False

    def anyconflicts(self):
        for appt in Appointment.objects.filter(Q(doctor=self.doctor) | Q(patient=self.patient)):
            if appt == self: continue
            if self.conflicts(appt):
                return appt
        return False

    def time_errors(self):
        '''
        Check start and end times for any problems.
        :return: Error message if invalid; None if valid
        '''
        print('**', self.start.time())
        min = datetime.time(8, 0)
        max = datetime.time(18, 0)
        if not((min <= self.start.time() < max) and (min < self.end.time() <= max)):
            return 'Appointments must be between 08:00 and 18:00.'
        if self.anyconflicts():
            return 'That time conflicts with another appointment.'
        if self.end < self.start:
            return 'End time must be after start time.'
        valid_durations = [60*x for x in (15, 30, 45, 60)]
        if (self.end - self.start).seconds not in valid_durations:
            return 'Duration must be 15, 30, 45, or 60 minutes.'
        if self.start < timezone.now():
            return 'Cannot change appointments in the past.'



class Prescription(models.Model):
    prescribed_By = models.ForeignKey(Doctor)
    prescribed_To = models.ForeignKey(Patient)
    name = models.CharField(max_length=50)
    end_Date = models.DateField()
    start_Date = models.DateField()
    usage = models.CharField(max_length=200)

    def __str__(self):
        return str(self.prescribed_To) + ' should follow these directions: \n'+ self.usage + '\nMedication: '+ self.name + '\nuntil ' + self.end_Date.isoformat() + '.\nContact '+ str(self.prescribed_By) + ' with any questions.'



class LogEntry(models.Model):

    user = models.ForeignKey(Person)
    #NOTE: we will store the time as UTC in the database. The django admin
    #interface automatically converts to local time when log entries are
    #viewed
    time = models.DateTimeField()
    log_types = (('c', 'Create'), ('r', 'Read'), ('u', 'Update'), ('d', 'Delete'))
    action_type = models.CharField(choices=log_types, max_length=1)
    thing_types = (('p','patient'), ('d','doctor'), ('n','nurse'), ('a','administrator'), ('v','appointment'), ('h','hospital'), ('r','prescription'), ('t','medical test'), ('m','message'))
    thing_type = models.CharField(choices=thing_types, max_length=1)
    thing_instance = models.IntegerField()  # pkid
    thing_field = models.CharField(max_length=25)
    # TODO: make this snake case
    eventDescription = models.CharField(max_length=200)

    def __str__(self):
        return self.user.username + ' ' + self.get_action_type_display() + ' ' + self.thing_type

    def parse(dateRange):
        if dateRange == None:
            logs = LogEntry.objects.all()
        else:
            logs = LogEntry.objects.filter(time__range=(dateRange[0], dateRange[1]))

        logList =   [" Log ",[0,0],{}]

        for log in logs:
            elements = str(log).split(' ')
            if(elements[2] == 'p'):
                logList = LogEntry.parseLog(logList, elements[1] ,"Patient")
            elif(elements[2] == 'd'):
                logList =  LogEntry.parseLog(logList, elements[1] ,"Doctor")
            elif(elements[2] == 'n'):
                logList =  LogEntry.parseLog(logList, elements[1] ,"Nurse")
            elif(elements[2] == 'a'):
                logList =  LogEntry.parseLog(logList, elements[1] ,"Administrator")
            elif(elements[2] == 'v'):
                logList = LogEntry.parseLog(logList, elements[1] ,"Appointment")
            elif(elements[2] == 'h'):
                logList =  LogEntry.parseLog(logList, elements[1] ,"Hospital")
            elif(elements[2] == 'r'):
                logList = LogEntry.parseLog(logList, elements[1] ,"Prescription")
        return logList

    def parseLog(logList, verb, noun):
        logList[1][0] = logList[1][0] + 1
        logList[0] = " Logs "
        logList[2] = LogEntry.parseVerb(logList[2], verb, noun)
        return logList
    def parseVerb(verbDic, verb, noun):
        if(verb in verbDic):
            verbDic[verb][1][0] += 1
            verbDic[verb][0] = " "+ verb + " Logs"
        else:
            verbDic[verb] = [" "+ verb + " Log", [1,1], {}]
        verbDic[verb][2] = LogEntry.parseNoun(verbDic[verb][2], verb, noun)
        return verbDic
    def parseNoun(nounDic, verb, noun):
        if(noun in nounDic):
            nounDic[noun][1][0] += 1
            nounDic[noun][0] = " "+ verb +" Logs For "+noun+ "s "
        else:
            nounDic[noun]= [" "+ verb +" Log For "+noun + "s ", [1,1], {}]
        return nounDic

class Message(models.Model):
    source = models.ForeignKey(Person, related_name='source')
    destination = models.ForeignKey(Person, related_name='destination')
    subject = models.CharField(max_length=100)
    body = models.CharField(max_length=1000)
    read = models.BooleanField(default=False)
    date = models.DateTimeField('Time sent')
