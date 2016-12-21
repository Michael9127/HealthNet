"""
filename: views.py
authors: Chris Lenter, Coleman Link, Mike Borkenstein, Rich Patulski, Sam Kilgore
purpose: the views for the HealthNetApp application
"""

from collections import defaultdict

import json
import random, string, datetime
from datetime import date
from django.utils import timezone
from django.db.utils import IntegrityError
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib import auth
from .forms import RegisterForm, LoginForm, ProfileForm, MedicalInformationForm, AppointmentForm, \
    PatientAppointmentForm, DoctorAppointmentForm, StaffRegisterForm, PrescriptionForm, MessageForm, MedicalTestForm, CustomDateForm

from .models import Patient, LogEntry, MedicalInformation, Appointment, Doctor, Nurse, Prescription, Hospital, Message, MedicalTest, MedicalProfessional, Administrator

from django.views.generic import FormView, DetailView, ListView
from .logger import *
from .statistics import *
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.validators import validate_email
from django.views.decorators.http import require_GET, require_POST
from os import path



def group_member(user, group):
    '''
    Determine if a user is a member of a certain group
    :param user: A Django auth.models.User
    :param group: (string) The group name
    :return: True iff the given user is part of the given group
    '''
    return user.groups.filter(name=group).exists()


def get_person_thing_type(user):
    '''
    Get the type of a logged-in user
    :param user: request.user
    :return: One of 'p', 'n', 'd', or 'a'
    '''
    if group_member(user, 'Patients'):
        return 'p'
    elif group_member(user, 'Nurses'):
        return 'n'
    elif group_member(user, 'Doctors'):
        return 'd'
    else:
        return 'a'


def get_person_thing_type_pkid(user):
    '''
    Get the specific user pk from a logged-in user
    :param user: request.user
    :return: A primary key
    '''
    if group_member(user, 'Patients'):
        return Patient.objects.get(username=user.username).pk
    elif group_member(user, 'Nurses'):
        return Nurse.objects.get(username=user.username).pk
    elif group_member(user, 'Doctors'):
        return Doctor.objects.get(username=user.username).pk
    else:
        #todo: actually return the person associated with the administrator
        return 0


def index(request):
    '''
    Choose which view to send the user to.
    '''
    user = request.user
    if user.is_staff or user.is_superuser:
        return HttpResponseRedirect(reverse('statisticscategories'))
    if group_member(user, 'Patients'):
        # Patients will want to see their profile
        return HttpResponseRedirect(reverse('updatepatient'))
    if group_member(user, 'Doctors') or group_member(user, 'Nurses'):
        # Doctors and nurses will want to see the patient listing.
        return HttpResponseRedirect(reverse('listpatients'))
    # otherwise, the user is not logged in.
    return HttpResponseRedirect('/app/login')


def register(request):
    '''
    Registration page for patients.
    '''
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if (data['password'] != data['cpassword']):
                # return an error
                return render(request, 'register.html', {'form': form, 'password_mismatch': True})
            try:#using builtin django email validate
                validate_email(data['email'])
            except ValidationError as ve:
                return render(request, 'register.html', {'form': form, 'invalid_email': True})
            today = date.today()
            birthday = data['date_of_birth']
            if( today < birthday) or (int(today.year) > int(birthday.year) + 150):
                #if birthday is in future, or birthday is over 150 years ago, it's probably not good
                return render( request, 'register.html', {'form': form, 'invalid_bday': True})
            try:
                user = User.objects.create_user(data['username'],
                                                data['email'],
                                                data['password'])
                user.groups.add(Group.objects.get(name='Patients'))
            except IntegrityError as e:
                # The username was probably not unique
                return render(request, 'register.html', {'form': form, 'username_taken': True})
            user.save()
            # Create a new patient that matches the user. Give them a blank 'MedicalInformation'
            # to start off.
            patient = Patient.objects.create(name=data['name'],
                                             username=data['username'],
                                             preferred_hospital=data['preferred_hospital'],
                                             contact_information=data['contact_information'],
                                             date_of_birth=data['date_of_birth'],
                                             emergency_contact=data['emergency_contact'],
                                             insurance_id=data['insurance_id'],
                                             medical_information=MedicalInformation.objects.create(history=''))




            patient.save()
            log_event(data['username'], 'c', 'p', patient.pk, 'all', 'patient was created')
            # Log the user in now that they've registered.
            u = auth.authenticate(username=data['username'], password=data['password'])
            if u is not None:
                auth.login(request, u)  # log the user in with provided credentials
                log_event(data['username'], 'r', 'p', patient.pk, 'N/A', 'user has logged in')
            return HttpResponseRedirect('/app/updatepatient')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


@login_required
def logout(request):
    '''
    logout the user. bring them to login page with redirect
    '''
    person = get_object_or_404(Person, username=request.user.username)
    ###################
    # log the logout
    #    if group_member(user, 'Patients'):
    #        log_event(request.user.username, 'r', 'p', person.pk, 'N/A', 'user has logged out')
    #    elif group_member(user, 'Nurses'):
    #        log_event(request.user.username, 'r', 'n', person.pk, 'N/A', 'user has logged out')
    #    elif group_member(user, 'Doctors'):
    #        log_event(request.user.username, 'r', 'd', person.pk, 'N/A', 'user has logged out')
    #    else:
    #        log_event(request.user.username, 'r', 'a', person.pk, 'N/A', 'user has logged out')

    log_event(request.user.username, 'r', get_person_thing_type(request.user), get_person_thing_type_pkid(request.user), 'N/A', 'user has logged out')

    auth.logout(request)
    return HttpResponseRedirect(reverse('login'))


def login(request):
    '''
    login page
    checks login credentials
    username not case-sensitive
    '''
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:  # Django contains functionality for disabling accounts.
                auth.login(request, user)  # Attach cookies to user's session
                if user.is_staff or user.is_superuser:
                    #log admin logins
                    log_event(username, 'r', get_person_thing_type(user), get_person_thing_type_pkid(user), 'N/A', 'user has logged in')
                    return HttpResponseRedirect(reverse('index'))
                # Otherwise, If not admin:
                # log the login.
                person = get_object_or_404(Person, username=user.username)
                log_event(username, 'r', get_person_thing_type(user), get_person_thing_type_pkid(user), 'N/A', 'user has logged in')
                if group_member(user, 'Patients'):
                    # Patients will want to see their profile;
                    # Doctors and nurses will want to see the patient listing.
                    return HttpResponseRedirect(reverse('index'))
                return HttpResponseRedirect(reverse('index'))
            else:
                pass
                # todo: Return a 'disabled account' error message (low priority)
        else:
            # That username/password combo is invalid. Notify the user by re-rendering the
            # template with an error message present.
            return render(request, 'login.html', {'form': LoginForm(request.POST),
                                                  'invalid_login': True})
    else:
        try:
            res = render(request, 'login.html', {'form': LoginForm()})
            return res
        except Exception as e:
            print(e)


@login_required
def updatePatient(request):
    '''
    This view is only for patients to update their profile.
    Patient can update their personal information, but not their medical information
    '''
    # Validate that the logged-in user is a patient, and
    # get the patient object we will need to modify.
    user = request.user
    if group_member(user, 'Patients'):
        patient = get_object_or_404(Patient, username=user.username)
        prescriptions = Prescription.objects.filter(prescribed_To=patient)
    else:
        return HttpResponseRedirect(reverse('login'))
    if request.method == 'POST':
        # The user clicked 'update'
        form = ProfileForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            patient.insurance_id = data['insurance_id']
            user.email = data['email']
            try:
                validate_email(data['email'])
            except ValidationError as ve:
                return render(request, 'updatepatient.html', {'form': form, 'invalid_email': True})
            if data['password'] and data['confirm_password']:
                if data['password'] != data['confirm_password']:
                    return render(request, 'updatepatient.html', {'form': form,
                                                                  'history': patient.medical_information.history,
                                                                  'password_mismatch': True})
                else:
                    user.set_password(data['password'])
                    user.save()
                    # With the password changed, we need to re-authenticate the user.
                    u = auth.authenticate(username=request.user.username, password=data['password'])
                    log_event(user.username, 'u', 'p', get_person_thing_type_pkid(u), 'N/A', 'user changed their password')
                    if u is not None:
                        auth.login(request, u)  # log the user in with provided credentials
                        log_event(user.username, 'r', 'p', get_person_thing_type_pkid(u), 'N/A', 'user logged in with new credentials')
            patient.save()
            user.save()
            # Now update the patient fields with newly provided information.
            patient.name = data['name']
            patient.preferred_hospital = data['preferred_hospital']
            patient.contact_information = data['contact_information']
            today = date.today()
            birthday = data['date_of_birth']
            if( today < birthday) or (int(today.year) > int(birthday.year) + 150):
                #if birthday is in future, or birthday is over 150 years ago, it's probably not good
                return render( request, 'updatepatient.html', {'form': form, 'invalid_bday': True})
            patient.date_of_birth = data['date_of_birth']
            patient.emergency_contact = data['emergency_contact']
            patient.save()
            log_event(user.username, 'u', 'p', patient.pk, 'N/A', 'user has updated profile')
            return HttpResponseRedirect('/app/updatepatient')
        else:
            return render(request, 'updatepatient.html', {'form': form})
    else:
        form = ProfileForm(initial={'name': patient.name,
                                    'username': patient.username,
                                    'preferred_hospital': patient.preferred_hospital,
                                    'email': user.email,
                                    'contact_information': patient.contact_information,
                                    'date_of_birth': patient.date_of_birth.isoformat(),
                                    'insurance_id' : patient.insurance_id,
                                    'emergency_contact': patient.emergency_contact
                                    })
    testList = MedicalTest.objects.filter(patient=patient)
    return render(request, 'updatepatient.html', {'form': form,
                                                  'prescription':prescriptions,
                                                  'history': patient.medical_information.history,
                                                  'tests': testList})


@login_required
def exportInformation(request):
    '''
    This view allows a patient to download their information as JSON.
    There is no form involved; this view is a static URL which generates the
     file when accessed.
    '''
    if not group_member(request.user, 'Patients'):
        return HttpResponseRedirect(reverse('login'))
    patient = get_object_or_404(Patient, username=request.user.username)
    prescriptions = Prescription.objects.filter(prescribed_To=patient)

    # Create a dictionary to store the exportable data
    info = {}
    # Information will consist of name, address, etc., all prescriptions, and
    # upcoming appointment information.
    # Add basic patient fields to the export dict
    for key in ('name', 'contact_information', 'username',
                'preferred_hospital', 'emergency_contact'):
        info[key] = str(getattr(patient, key))
    info['date_of_birth'] = patient.date_of_birth.isoformat()
    info['prescription'] = [str(p) for p in prescriptions] #prescriptionsStringList
    info['history'] = patient.medical_information.history
    # List all the appointments as well
    appts = []
    for appointment in patient.list_appointments():
        appts.append({
            'start': appointment.start.isoformat(),
            'end': appointment.end.isoformat(),
            'doctor': appointment.doctor.name,
            'hospital': appointment.hospital.name
        })
    info['appointments'] = appts
    # aaand all the test results
    info['tests'] = [t.dump() for t in MedicalTest.objects.filter(patient=patient)]

    data = json.dumps(info, indent=2)  # convert export dict to string
    # Offer as a download, not as a webpage.
    resp = HttpResponse(data, content_type='application/x-download')
    resp['Content-Disposition'] = 'attachment;filename=export.json'
    log_event(request.user.username, 'r', get_person_thing_type(request.user), get_person_thing_type_pkid(request.user), 'All', 'user has exported information as json');
    return resp


@login_required
def updatePatientMedicalInformation(request, patient_pk):
    '''
    This view is for doctors and nurses who want to edit a patient's Medical information
    for example: medical history
    '''
    p = get_object_or_404(Patient, pk=patient_pk)
    # permissions check
    if group_member(request.user, 'Patients'):
        # Patients can't write their own prescriptions
        return HttpResponseRedirect(reverse('login'))
    if group_member(request.user, 'Nurses'):
        n = get_object_or_404(Nurse, username=request.user.username)
        # Requirement 10: nurses can only view patient medical information in the hospital they work for.
        if p.preferred_hospital != n.hospital:
            return HttpResponseRedirect(reverse('login'))
    mi = p.medical_information

    if request.method == "POST":
        form = MedicalInformationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # Only doctors can edit prescriptions.
            # TODO: update when prescription implementation changes.
            if group_member(request.user, 'Doctors'):
                pass #todo might add prescription functionailty here
            mi.history = data['history']
            mi.save()
            log_event(request.user.username, 'u', 'p', p.pk, 'N/A', 'doctor has updated patient\'s medical information')

            return HttpResponseRedirect(reverse('listpatients'))
    else:  # HTTP GET
        form = MedicalInformationForm(initial={'history': mi.history})
        if group_member(request.user, 'Nurses'):
            pass #todo add prescription form.fields['prescription'].widget.attrs['readOnly'] = True
        # Handle "linking" emergency contact information
        other_contact = Person.objects.filter(username=p.emergency_contact)
        if other_contact.exists():
            e_contact = other_contact[0].contact_information
        else:
            e_contact = p.emergency_contact
        return render(request, 'prescribe.html', {'patient': p,
                                                  'form': form,
                                                  'e_contact': e_contact})

@login_required
@require_GET
def listPrescriptions(request, patient_pk):
    '''
    a doctor, nurse, or admin can list the prescriptions of a
    patient that is specified by the patient_pk param
    :param request:
    :param patient_pk: pk id for the patient to view prescriptions for
    '''
    # if group_member(request.user, 'Nurses')  or request.user.is_superuser:
    patient = get_object_or_404(Patient, pk=patient_pk)
    prescriptions = Prescription.objects.filter(prescribed_To=patient)
    # else:
    #     patient = get_object_or_404(Patient, pk=patient_pk)
    #     doc = get_object_or_404(Doctor, username=request.user.username)
    #     prescriptions = Prescription.objects.filter(prescribed_By=doc, prescribed_To=patient)

    log_event(request.user.username, 'r', 'p', patient_pk, 'prescriptions', 'user has listed patient\'s prescriptions')

    if not prescriptions:
        return render(request, 'listPrescriptions.html', {'patient': patient, 'noPrescriptions': True})

    return render(request, 'listPrescriptions.html', {'patient': patient, 'prescriptions': prescriptions})

@login_required
@require_GET
def deletePrescription(request, patient_pk, prescription_pk):
    '''
    delete this prescription for this patient
    :param request:
    :param patient_pk: patient to delete this prescription from
    :param prescription_pk: the prescription to delete
    '''
    pre = get_object_or_404(Prescription, pk=prescription_pk)
    pre.delete()
    log_event(request.user.username, 'd', 'r', prescription_pk, 'All', 'a prescription was deleted')
    return HttpResponseRedirect(reverse('listPrescriptions', args=(patient_pk,)))

@login_required
def removeTest(request, patient_pk, test_pk):
    '''
    deletes a test from the database
    :param request:
    :param patient_pk: patient whose tests to delete
    :param test_pk: test to delete
    :return:
    '''
    test=get_object_or_404(MedicalTest,pk=test_pk)
    test.delete()
    log_event(request.user.username, 'd', 't', test_pk, 'All', 'a medical test was deleted')
    return HttpResponseRedirect(reverse('listTests',args=(patient_pk,)))

@login_required
@require_POST
def acceptPrescriptionForm(request, patient_pk):
    patient = get_object_or_404(Patient, pk=patient_pk)
    doc = get_object_or_404(Doctor, username=request.user.username)

    form = PrescriptionForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        if group_member(request.user, 'Doctors'):
            prescription = Prescription.objects.create(prescribed_By=doc,
                                                       prescribed_To=patient,
                                                       name=data['name'],
                                                       start_Date=datetime.date.today(),
                                                       end_Date=data['end_Date'],
                                                       usage=data['usage'])
            prescription.save()

            log_event(request.user.username, 'c', 'r', prescription.pk, 'All', 'A prescription was created')
            return HttpResponseRedirect(reverse('listPrescriptions', args=(patient_pk,)))
        else:
            pass #todo redirect un privilege users
    else:
        return render(request, 'prescriptionForm.html', {'form': form, 'patientName': patient.name,'patient_pk': patient_pk})

@login_required
def listTests(request, patient_pk):
    '''
    list all of the tests for this patient
    :param request:
    :param patient_pk:
    :return:
    '''
    patient = get_object_or_404(Patient, pk=patient_pk)
    tests = MedicalTest.objects.filter(patient=patient )#only view this patient's tests
    log_event(request.user.username, 'r', 'p', patient_pk, 'medical tests', 'the patients medical tests were listed')
    return render(request, 'listTests.html',{'patient':patient,'tests':tests})


@login_required
def receiveMedicalTest(request,patient_pk):
    '''
    when uploading a test, this is where the request is sent.
    creates a new test with given information
    :param request:
    :param patient_pk: patient to create test for
    '''
    patient = get_object_or_404(Patient, pk=patient_pk)
    form = MedicalTestForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data
        if group_member(request.user, 'Doctors') or group_member(request.user, 'Nurses'):
            pictures = request.FILES.get('pictures', None)
            pictures1 = request.FILES.get('pictures1', None)
            pictures2 = request.FILES.get('pictures2', None)
            pictures3 = request.FILES.get('pictures3', None)
            test = MedicalTest.objects.create(title=data['title'],
                                              testDate=data['testDate'],
                                              results=data['results'],
                                              doctor=data['doctor'],
                                              patient=patient,
                                              pictures=pictures,
                                              pictures1=pictures1,
                                              pictures2=pictures2,
                                              pictures3=pictures3,
                                              pending=0,
                                              hospital=data['hospital'],)

            test.save()
            log_event(request.user.username, 'c', 'm', patient.pk, 'N/A', 'user has uploaded a Medical Test')
            return HttpResponseRedirect(reverse('listTests', args=(patient_pk,)))
    else:
        return render(request, 'uploadMedicalInformation.html', {'form': form, 'patient_pk':patient.pk})

@login_required
def confirmTest(request, test_pk, patient_pk):
    '''
    a doctor can confirm/release test results
    :param request:
    :param test_pk: the test to confirm
    :param patient_pk: patient's test
    '''
    test = MedicalTest.objects.get(pk=test_pk)
    test.pending=1
    test.save()
    return HttpResponseRedirect(reverse('viewTestForm', args=(test_pk,0,)))

@login_required
def editTest( request, test_pk):
    '''
    this is where the requests go so that a doctor, nurse, or admin can edit a previously
    existing test
    :param request:
    :param test_pk: the test to edit
    '''
    test = MedicalTest.objects.get(pk=test_pk)
    patient_pk = test.patient.pk
    if test.pending==1:
        pend=False
    else: pend=True
    if request.method == 'POST':
        form = MedicalTestForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            #this was added so that pictures are only overwritten when
            #the user actually uploads a new picture in this form spot.
            #previously, if a picture was uploaded, then edited without reuploading the same
            #or a new pic, the original picture was removed.
            if not test.pictures or request.FILES.get('pictures', None):#if we don't already have a picture
                pictures = request.FILES.get('pictures', None)#get what's already there
            else:#we do have a picture
                pictures = test.pictures#we don't want to add a different one, keep it the same
            if not test.pictures1 or request.FILES.get('pictures1', None):
                pictures1 = request.FILES.get('pictures1', None)
            else:
                pictures1 = test.pictures1
            if not test.pictures2 or request.FILES.get('pictures2', None):
                pictures2 = request.FILES.get('pictures2', None)
            else:
                pictures2 = test.pictures2
            if not test.pictures3 or request.FILES.get('pictures3', None):
                pictures3 = request.FILES.get('pictures3', None)
            else:
                pictures3 = test.pictures3
            test.title = data['title']
            test.testDate= data['testDate']
            test.doctor = data['doctor']
            test.hospital=data['hospital']
            test.results=data['results']
            test.pictures=pictures
            test.pictures1=pictures1
            test.pictures2=pictures2
            test.pictures3=pictures3
            test.save()
            log_event(request.user.username, 'u', 't', test_pk, 'All', 'A medical test was edited')
            return render(request, 'viewTest.html',{'test': test, 'pend': pend, 'patient_pk': patient_pk})
    return HttpResponseRedirect(reverse('listTests', args=(patient_pk,)))


@login_required
def viewTestForm(request, test_pk, edit):
    '''
    the to view or redirect to editing the test.
    :param request:
    :param test_pk: the test to edit
    :param edit: whether we can edit the medicalTest or not
    '''
    #edit is 2 if the user will edit
    #otherwise, it's zero
    test = MedicalTest.objects.get(pk=test_pk)
    patient_pk=test.patient.pk
    patient = Patient.objects.get(pk=patient_pk)
    if request.method != 'POST' and (group_member(request.user, 'Doctors') or group_member(request.user, 'Nurses')) and int(edit)==2:#called by doctor and wants to edit the information
        form=MedicalTestForm(initial={'title': test.title,
                                    'testDate': test.testDate,
                                    'doctor': test.doctor,
                                      'patient': test.patient,
                                      'hospital': test.hospital,
                                      'results': test.results,
                                      'pictures': test.pictures,
                                      'pictures1': test.pictures1,
                                      'pictures2': test.pictures2,
                                      'pictures3': test.pictures3,
                                    })
        return render(request, 'uploadMedicalInformation.html',{'form': form, 'patientName': patient.name,'patient_pk': patient_pk,
                'editing': True, 'test_pk':test.pk})
    else:# will be called from the listing of tests viewed from patient's login
        if( test.pending==1 ):#not pending, it's confirmed
            pend=False
        else: pend=True
        return render(request, 'viewTest.html',{'test': test, 'pend': pend, 'patient_pk': patient_pk})

@login_required
def getTestForm(request,patient_pk):
    '''
    just a midway point when uploading a Test. Makes things a tad bit nicer
    :param request:
    :param patient_pk: patient who has the test
    '''
    patient = get_object_or_404(Patient, pk=patient_pk)
    form = MedicalTestForm()
    return render(request, 'uploadMedicalInformation.html', {'form': form, 'patientName': patient.name,'patient_pk': patient_pk, 'editing': False})

@login_required
@require_GET
def getPrescriptionForm(request, patient_pk):
    patient = get_object_or_404(Patient, pk=patient_pk)
    form = PrescriptionForm()
    return render(request, 'prescriptionForm.html', {'form': form, 'patientName': patient.name,'patient_pk': patient_pk})


@login_required
def admitPatient(request, patient_pk):
    '''
    admitting a patient to a hospital
    :param request:
    :param patient_pk: the patient being admitted
    '''
    #if the user is just viewing the patient's current admissions
    if request.method == "GET":
        #if user is a medical professional, get the user's cooresponding medical_professional object
        if group_member(request.user, 'Nurses'):
            mp = get_object_or_404(Nurse, username=request.user.username)
        elif group_member(request.user, 'Doctors'):
            mp = get_object_or_404(Doctor, username=request.user.username)
        elif request.user.is_superuser:
            mp = get_object_or_404(Administrator, username=request.user.username)
        #otherwise, the user is logged in as a patient
        else:
            #redirect them to the login page
            return HttpResponseRedirect(reverse('login'))
        #get the user object associated with the request
        user = request.user
        #get the patient who's admission status is being viewed
        patient = get_object_or_404(Patient, pk=patient_pk)
        #return the patient's current admissions page
        return render(request, 'admitPatient.html', {'medical_prof': mp, 'user': user, 'patient': patient, 'hospitals': Hospital.objects.all()})

    #otherwise, the patient's admission status is being modified (ie: a POST request)
    else:
        #if user is an administrator
        if request.user.is_staff or request.user.is_superuser:

            #find the patient primary key within the POST data
            key = next(x for x in request.POST.keys() if x.isnumeric())
            #get the integer value of the patient primary key
            patient_pk = int(key)
            #get the patient who's admitted_to hospital was set
            patient = get_object_or_404(Patient, pk=patient_pk)
            #get the hospital that the patient's admitted_to was changed to
            hsptl_name = request.POST[key]

            #get the hospital object cooresponding to the hospital name, or None
            if hsptl_name != 'None':
                hsptl = get_object_or_404(Hospital, name=hsptl_name)
            else:
                hsptl = None

            #admit/discharge the patient to the specified hospital, then save the change
            patient.admitted_to = hsptl;
            #save the change to the database
            patient.save()

            #log the patient hospital update
            log_event(request.user.username, 'u', 'p', patient.pk, 'admitted_to', 'the hospital the patient was addmitted to was changed')

            #redirect the admin to the current admit patient page
            return HttpResponseRedirect(reverse('admit_patient', kwargs={'patient_pk': patient_pk}))

        #otherwise, if the user is a doctor or a nurse
        elif group_member(request.user, 'Doctors') or group_member(request.user, 'Nurses'):
            #find the patient primary key within the POST data
            key = next(x for x in request.POST.keys() if x.isnumeric())
            #get the integer value of the patient primary key
            patient_pk = int(key)
            #get the patient who's admission status is being modified
            patient = get_object_or_404(Patient, pk=patient_pk)
            #get the name of the action that is being performed on the patient's admission status
            action = request.POST[key]

            #get the hospital of the current user
            hsptl = MedicalProfessional.objects.get(username=request.user.username).hospital

            #if the patient is not admitted to any hospital, and the user is admitting them
            if ((patient.admitted_to is None) and (action[0:5] == 'Admit')):
                #get the reason for admitting the patient (if applicable) - if not found, set value to 'None'
                reason = request.POST.get('reason', 'None')
                #set the patient's hospital to that of the user
                patient.admitted_to = hsptl
                #save the change to the database
                patient.save()
                #log the patient hospital admission
                log_event(request.user.username, 'u', 'p', patient.pk, 'admitted_to', 'patient was admitted to ' + hsptl.name + ' with reason \"' + reason + '\"')

            #the user is a doctor and is transferring a patient
            elif (group_member(request.user, 'Doctors') and (action == 'Transfer')):
                #save the hosital the patient was previously admitted to
                old_hsptl = patient.admitted_to
                #set the patient's hospital to that of the user
                patient.admitted_to = hsptl
                #save the change to the database
                patient.save()
                #log the patient hospital transfer
                log_event(request.user.username, 'u', 'p', patient.pk, 'admitted_to', 'the patient was transfered from ' + old_hsptl.name + ' to ' + hsptl.name)


            #otherwise, if the user is a doctor, and is discharging a patient from their own hospital
            elif group_member(request.user, 'Doctors') and (action == 'Discharge') and (patient.admitted_to == hsptl):
                #set the patient to be admitted to no hospital
                patient.admitted_to = None
                #save the change to the database
                patient.save()
                #log the patient hospital discharge
                log_event(request.user.username, 'u', 'p', patient.pk, 'admitted_to', 'the patient was discharged from ' + hsptl.name)

            #redirect the user to the current admit patient page
            return HttpResponseRedirect(reverse('admit_patient', kwargs={'patient_pk': patient_pk}))

        #otherwise, the user is logged in as a patient, redirect them to the login form
        else:
            return HttpResponseRedirect(reverse('login'))



@login_required
def listPatients(request):
    '''
    Doctors can view all of their current patients
    '''
    # make sure logged in as Doctor or nurse
    # Nurses can only view patient medical information in the hospital they work for.
    if group_member(request.user, 'Nurses'):
        mp = get_object_or_404(Nurse, username=request.user.username)
        queryset = mp.list_patients()
    elif group_member(request.user, 'Doctors'):
        mp = get_object_or_404(Doctor, username=request.user.username)
        queryset = mp.list_patients()
    elif request.user.is_superuser:
        mp = get_object_or_404(Administrator, username=request.user.username)
        queryset = mp.list_patients()
    else:
        return HttpResponseRedirect(reverse('login'))
    user = request.user

    log_event(user.username, 'r', 'p', get_person_thing_type_pkid(user), 'N/A', 'user has viewed list of patients')
    return render(request, 'ListPatients.html', {'patients': queryset, 'user': user})


@login_required
def calendar(request):
    '''
    the calendar view used mainly for viewing appointments for a user
    '''
    appts = []
    can_create = True
    if group_member(request.user, 'Patients'):
        u = get_object_or_404(Patient, username=request.user.username)
        if not u.can_create_appointment():
            # Disable the new appointment button if a patient has outstanding appointments.
            can_create = False
    elif group_member(request.user, 'Doctors'):
        u = get_object_or_404(Doctor, username=request.user.username)
    elif group_member(request.user, 'Nurses'):
        u = get_object_or_404(Nurse, username=request.user.username)
    elif request.user.is_superuser:
        u = get_object_or_404(Administrator, username=request.user.username)
    else:
        return HttpResponseRedirect(reverse('login'))
    # Polymorphic / duck-typed list_appointments function differs in behavior
    # based on the type of logged-in user. See models.py.
    for appointment in u.list_appointments():
        print(appointment.start.time())
        appts.append(
            {'title': u.appointment_title(appointment),
             'start': appointment.start.isoformat(),
             'end': appointment.end.isoformat(),
             'allDay': False,
             'url': reverse('update_appointment', kwargs={'appointment_pk': appointment.pk})
             })
    return render(request, 'calendar.html', {'appointments': json.dumps(appts),
                                             'can_create': can_create})


@login_required
def update_appointment(request, appointment_pk):
    '''
    update details on an existing appointment
    '''
    a = get_object_or_404(Appointment, pk=appointment_pk)
    old_a_start = a.start
    old_a_end = a.end
    # A patient can only update their appointments
    if group_member(request.user, 'Patients'):
        p = get_object_or_404(Patient, username=request.user.username)
        if p != a.patient:
            return HttpResponseRedirect(reverse('login'))
    # Everyone else can update any appointment
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            local_start = datetime.datetime.combine(data['date'], data['start_time'])
            local_end = datetime.datetime.combine(data['date'], data['end_time'])
            # change timezone from local to UTC
            a.start = make_aware(local_start, get_default_timezone())
            a.end = make_aware(local_end, get_default_timezone())
            a.hospital = data['hospital']
            errors = a.time_errors()
            if errors:
                # Revert times to saved times
                a.start = old_a_start
                a.end = old_a_end
                return render(request, 'updateappointment.html', {'form': form,
                                                                  'errors': errors,
                                                                  'appointment': a})
            else:
                a.save()
                log_event(request.user.username, 'u', 'v', appointment_pk, 'N/A', 'user has updated an appointment')

                return HttpResponseRedirect(reverse('Calendar'))
        else:
            return render(request, 'updateappointment.html', {'form': form,
                                                              'appointment': a})
    else:  # HTTP GET
        # change timezone from stored (UTC) to local
        local_start = a.start.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
        local_end = a.end.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
        form = AppointmentForm(initial={'date': a.start.date(),
                                        'start_time': local_start,
                                        'end_time': local_end,
                                        'hospital': a.hospital,})
        return render(request, 'updateappointment.html', {'appointment': a,
                                                          'form': form})


@login_required
def cancel_appointment(request, appointment_pk):
    '''
    cancel an existing appointment for a user
    '''
    a = get_object_or_404(Appointment, pk=appointment_pk)
    if group_member(request.user, 'Patients'):
        # A patient can only cancel their own appointments
        p = get_object_or_404(Patient, username=request.user.username)
        if p != a.patient:
            return HttpResponseRedirect(reverse('login'))
    elif group_member(request.user, 'Nurses'):
        # Requirement 7: Nurses cannot cancel appointments
        return HttpResponseRedirect(reverse('login'))
    elif group_member(request.user, 'Doctors'):
        # A doctor can only cancel their own appointments
        d = get_object_or_404(Doctor, username=request.user.username)
        if d != a.doctor:
            return HttpResponseRedirect(reverse('login'))
    else:
        return HttpResponseRedirect(reverse('login'))

    # Successfully passed all checks. Delete the appointment
    log_event(request.user.username, 'd', 'v', appointment_pk, 'N/A', 'user has deleted this appointment')
    a.delete()
    return HttpResponseRedirect(reverse('Calendar'))


@login_required
def create_appointment(request):
    '''
    user can create an appointment
    Patient users can only have one appointment in total (for now)
    Other users can have multiple
    '''
    if request.method == "POST":
        if group_member(request.user, 'Patients'):
            form = PatientAppointmentForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                p = get_object_or_404(Patient, username=request.user.username)
            else:
                return render(request, 'CreateAppointment.html', {'form': form})
        else:
            form = DoctorAppointmentForm(request.POST, patient_list=Patient.objects.all())
            if form.is_valid():
                data = form.cleaned_data
                p = data['patient']
            else:
                return render(request, 'CreateAppointment.html', {'form': form})
        start = datetime.datetime.combine(data['date'], data['start_time'])
        end = datetime.datetime.combine(data['date'], data['end_time'])
        start = make_aware(start, get_default_timezone())
        end = make_aware(end, get_default_timezone())
        a = Appointment.objects.create(start=start,
                                       end=end,
                                       doctor=data['doctor'],
                                       hospital=data['hospital'],
                                       patient=p)
        errors = a.time_errors()
        if errors:
            a.delete()
            return render(request, 'CreateAppointment.html', {'form': form,
                                                              'errors': errors,})
        else:
            a.save()
            log_event(request.user.username, 'c', 'v', a.pk, 'N/A', 'user has created an appointment')
            return HttpResponseRedirect(reverse('Calendar'))

    else:
        if group_member(request.user, 'Patients'):
            p = get_object_or_404(Patient, username=request.user.username)
            if not p.can_create_appointment():
                return HttpResponseRedirect(reverse('Calendar'))
            form = PatientAppointmentForm(initial={'hospital': p.preferred_hospital})
            return render(request, 'CreateAppointment.html', {'form': form})
        elif group_member(request.user, 'Doctors'):
            d = get_object_or_404(Doctor, username=request.user.username)
            form = DoctorAppointmentForm(patient_list=d.list_patients(), initial={'hospital': d.hospital,
                                                                                  'doctor': d})
            return render(request, 'CreateAppointment.html', {'form': form})
        elif group_member(request.user, 'Nurses'):
            n = get_object_or_404(Nurse, username=request.user.username)
            form = DoctorAppointmentForm(patient_list=n.list_patients(), initial={'hospital': n.hospital})
            return render(request, 'CreateAppointment.html', {'form': form})
        else:
            return HttpResponseRedirect(reverse('login'))


@login_required
def view_logs(request):
    '''
    admins and other staff can view log entries
    '''
    #    if(user.is_superuser || user.is_staff):
    if request.user.is_staff or request.user.is_superuser:
        queryset = LogEntry.objects.all().order_by('-time')
        paginator = Paginator(queryset, 10) # 10 per page
        page = request.GET.get('page')
        try:
            log_page = paginator.page(page)
        except PageNotAnInteger:
            log_page = paginator.page(1)
        except EmptyPage: # out of range
            log_page = paginator.page(paginator.num_pages)

        return render(request, 'ListLogEntries.html', {'log_entries': log_page})
    else:
        return render(request, 'login.html', {'auth_error': 'Only administrators may view system logs.', 'form': LoginForm()})


@login_required
def view_logs_by_user(request, person_pk):
    '''
    the admin or other staff can view logs based on a particular user
    '''
    if request.user.is_staff or request.user.is_superuser:
        person_object = get_object_or_404(Person, pk=person_pk)
        queryset = LogEntry.objects.filter(user=person_object).order_by('-time')
        paginator = Paginator(queryset, 10) # 10 per page
        page = request.GET.get('page')
        try:
            log_page = paginator.page(page)
        except PageNotAnInteger:
            log_page = paginator.page(1)
        except EmptyPage: # out of range
            log_page = paginator.page(paginator.num_pages)
        return render(request, 'ListLogEntries.html', {'log_entries': log_page, 'by_user': person_object.name})
    else:
        return render(request, 'login.html', {'auth_error': 'Only administrators may view system logs.', 'form': LoginForm()})


@login_required
def register_staff(request):
    '''
    admins can register other admins, doctors, or nurses.
    '''
    # Only admins can do this
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseRedirect(reverse('login'))
    if request.method == "POST":
        form = StaffRegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if data['password'] != data['cpassword']:
                # return an error
                return render(request, 'registerstaff.html', {'form': form, 'password_mismatch': True})
            try:#using builtin django email validate
                validate_email(data['email'])
            except ValidationError as ve:
                return render(request, 'registerstaff.html', {'form': form, 'invalid_email': True})
            today = date.today()
            birthday = data['date_of_birth']
            if( today < birthday) or (int(today.year) > int(birthday.year) + 150):
                #if birthday is in future, or birthday is over 150 years ago, it's probably not good
                return render( request, 'registerstaff.html', {'form': form, 'invalid_bday': True})


            # Reverse the ChoiceField (selection comes back as int; more readable
            # to convert it to a string)
            user_type = ["admin", "doctor", "nurse"][int(data['user_type'])]
            try:
                if user_type == "admin":
                    u = User.objects.create_superuser(username=data['username'],
                                                      password=data['password'],
                                                      email=data['email'])
                    u.save()
                    u2 = Person.objects.create(name=data['name'],
                                              date_of_birth=data['date_of_birth'],
                                              contact_information=data['contact_information'],
                                              username=data['username'])
                    u2.save()
                else:
                    if user_type == "doctor":
                        group = Group.objects.get(name='Doctors')
                        model = Doctor
                    else:  # nurse
                        group = Group.objects.get(name='Nurses')
                        model = Nurse
                    u = User.objects.create_user(username=data['username'],
                                                 password=data['password'],
                                                 email=data['email'])
                    u.groups.add(group)
                    u.save()
                    u2 = model.objects.create(name=data['name'],
                                              username=data['username'],
                                              hospital=data['hospital'],
                                              contact_information=data['contact_information'],
                                              date_of_birth=data['date_of_birth'])
                    u2.save()
                # show a success message on the same page
                form = StaffRegisterForm()
                log_event(request.user.username, 'c', get_person_thing_type(User.objects.get(username=data['username'])), u2.pk, 'all', 'created a new staff member')
                return render(request, 'registerstaff.html', {'form': form,
                                                              'created': data['username']})
            except IntegrityError:
                # Very likely the username is already taken.
                return render(request, 'registerstaff.html', {'form': form,
                                                              'username_taken': True})
        else:
            # Invalid form. Re-render it, displaying any errors (handled by the template)
            return render(request, 'registerstaff.html', {'form': form})
    else:
        form = StaffRegisterForm()
        return render(request, 'registerstaff.html', {'form': form})

@login_required
def list_messages(request):
    '''
    the user can list their messages in their inbox
    '''
    recipient = get_object_or_404(Person, username=request.user.username)
    messages = recipient.get_messages()
    paginator = Paginator(messages, 10) # 10 per page
    page = request.GET.get('page')
    try:
        message_page = paginator.page(page)
    except PageNotAnInteger:
        message_page = paginator.page(1)
    except EmptyPage: # out of range
        message_page = paginator.page(paginator.num_pages)
    log_event(request.user.username, 'r', get_person_thing_type(request.user), get_person_thing_type_pkid(request.user), 'messages', 'the users messages were listed')
    return render(request, 'listMessages.html', {'Messages':message_page})

@login_required
def view_message(request, messageID):
    '''
    view the message that was clicked
    :param request:
    :param messageID: the id of the message to click
    '''
    message = get_object_or_404(Message, pk=messageID)
    user = get_object_or_404(Person, username=request.user.username)
    if message.destination != user:
        raise Http404("No message for you")
    message.read = True
    message.save()
    log_event(request.user.username, 'r', 'm', messageID, 'All', 'The message was viewed')
    return render(request, 'ViewMessage.html',{'Message':message})


@login_required
def send_message(request):
    '''
    send a message to another user in the message
    '''
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            sender = get_object_or_404(Person, username=request.user.username)
            receiver = data['destination']
            message = Message.objects.create(destination=receiver,
                                   source=sender,
                                   subject=data['subject'],
                                   body=data['body'],
                                   date=timezone.now() )
            log_event(request.user.username, 'c', 'm', message.pk, 'All', 'A message was created and sent')
            return HttpResponseRedirect('/app/listmessages')
    else:
        form = MessageForm()
    return render(request, 'SendMessage.html', {'form': form})

@login_required
def reply(request, message_pk):
    '''
    reply to a message that was received
    '''
    if request.method == 'POST':
        return send_message(request)
    else:
        # Ugly hack
        MessageForm.base_fields['destination'].initial=Message.objects.get(pk=message_pk).source
        MessageForm.base_fields['subject'].initial="Re: " + Message.objects.get(pk=message_pk).subject
        form = MessageForm()
        MessageForm.base_fields['destination'].initial = None
        MessageForm.base_fields['subject'].initial = None
    return render(request, 'SendMessage.html', {'form': form})

@login_required
@require_GET
def d3Statistics(request):
    if not (request.user.is_superuser):
        return HttpResponseRedirect(reverse('login'))

    form = CustomDateForm(request.GET)
    start = request.GET.get('start')
    end = request.GET.get('end')
    dateRange = []
    MAXDAYS = 10000
    dateRange.append(start)
    dateRange.append(end)

    if not start:
        start = datetime.date.today() - datetime.timedelta(days=MAXDAYS )
        dateRange[0] = start
    if not end:
        end = datetime.date.today() + datetime.timedelta(days=1 )
        dateRange[1] = end
    if not form.is_valid():
        return render(request, 'D3Logger.html',{'data': None, 'form': form})
    return render(request, 'D3Logger.html',{'data': json.dumps(LogEntry.parse(dateRange)), 'form': form})





@login_required
@require_GET
def system_statistics_categories(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseRedirect(reverse('login'))
    return render(request, 'StatisticsCategories.html')

@login_required
@require_GET
def system_statistics(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseRedirect(reverse('login'))

    metric = request.GET.get('metric')
    days = request.GET.get('days')
    start = request.GET.get('start')
    end = request.GET.get('end')

    # Converts number of days to start and end dates
    if days:
        if days.isdigit():
            start = datetime.date.today() - datetime.timedelta(days=int(days))
            end = datetime.date.today()
            print("+++++++++++", start, end)
        else:
            raise Http404('bad day count')
    # Checks if both dates were provided, if not uses 10000 as terminal boundaries
    else:
        MAXDAYS = 10000
        if not start:
            start = datetime.date.today() - datetime.timedelta(days=MAXDAYS )
        if not end:
            end = datetime.date.today() + datetime.timedelta(days=MAXDAYS)


    form = CustomDateForm(request.GET)

    if metric ==  'prescriptions':
        heading = ['Name', 'Amount of Prescriptions']
        prescriptions = []
        if form.is_valid():
            prescriptions = prescriptionStats(start, end)
        return render(request, 'StatisticsTable.html', {'form':form, 'heading':heading,'elements': prescriptions})


    elif metric == 'PatientAppointments':
        heading = ['Patient', 'Number of Appointments']
        appointments = []
        if form.is_valid():
            appointments = patientAppointmentStats(start, end)
        return render(request, 'StatisticsTable.html', {'form':form,'heading':heading,'elements': appointments})

    elif metric == 'staylength':
        heading = ['Patient', 'Average Length of Appointment']
        avgAppLength = []
        if form.is_valid():
            avgAppLength = patientAppointmentLengthStats(start, end)
        return render(request, 'StatisticsTable.html', {'form':form,'heading':heading,'elements': avgAppLength})

    elif metric == 'AppointmentAverages':
        appointmentCount = None
        avgAppLength = 0
        if form.is_valid():
            appointmentCount = hospitalAppointmentStats(start, end)
            avgAppLength = hospitalAppointmentLengthStats(start, end)
        return render(request, 'StatisticsPanel.html',{'form':form, 'length':avgAppLength, 'count':appointmentCount})

    elif metric == 'AdmissionReasons':
        heading = ['Admission Reason', 'Amount of Admissions']
        admissionReasons = []
        if form.is_valid():
            admissionReasons = hospitalAdmissionReasons(start, end)
        return render(request, 'StatisticsTable.html', {'form':form,'heading':heading,'elements': admissionReasons})
    else:
        raise Http404(metric+": Not a Stat")






@login_required
@require_GET
def view_log_entry(request, log_entry_pk):
    '''
    view a particular log entry based on the pk passed in
    '''
    #if the user is not an administrator
    if not (request.user.is_staff or request.user.is_superuser):
        #redirect them to the login page
        return HttpResponseRedirect(reverse('login'))

    #get the specified log entry object from the database
    entry = get_object_or_404(LogEntry, pk=log_entry_pk)

    #return a template containing the information in the log entry
    return render(request, 'viewLogEntry.html', {'entry': entry})


@login_required
def emergency_register_patient(request):
    '''
    emergency registration for a patient
    no fields are required and a random string is generated for both the username and password
    '''
    user = request.user
    if not (group_member(user, 'Doctors') or group_member(user, 'Nurses') or user.is_staff or user.is_superuser):
        return HttpResponseRedirect(reverse('login'))

    if(request.method == 'GET'):
        while True:
            random_username = ''.join(random.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(7))
            try:
                User.objects.get(username=random_username)
            except User.DoesNotExist:
                break;

        random_password = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(12))
        form = RegisterForm()
        return render(request, 'emergency_register.html', {'form': form, 'username': random_username, 'password': random_password})


    elif(request.method == 'POST'):
        form = RegisterForm(request.POST)

        if form.is_valid() or not form.is_valid():
            data = form.cleaned_data

            #if there was no username or no password specified in the port data
            if (request.POST.get('username', '') == '') or (request.POST.get('password', '') == ''):
                #redirect the user to the emergency registration page
                return HttpResponseRedirect(reverse('emergencyregistration'))

            try:
                #create a new user object for the new patient
                new_user = User.objects.create_user(request.POST['username'], "", request.POST['password'])
                #add the new user to the Patients group
                new_user.groups.add(Group.objects.get(name='Patients'))
            except IntegrityError as e:
                # The username was probably not unique
                return render(request, 'emergency_register.html', {'form': form})

            #save the user object
            user.save()

            #if user is an administrator
            if user.is_superuser or user.is_staff:
                #assign patient to the first hospital (administrators are expeced to change this manually, if necessary)
                hsptl = Hospital.objects.get(pk=1)
            else:
                #get the hospital the user works for
                hsptl = MedicalProfessional.objects.get(username=user.username).hospital

            new_patient_name = data.get('name', '')
            if new_patient_name == '':
                new_patient_name = request.POST['username'] + '   ' + str(datetime.date.today())

            #create the new patient, using any available information, and leaving default/blank values elsewhere
            patient = Patient.objects.create(name=new_patient_name,
                    username=request.POST['username'],
                    preferred_hospital=hsptl,
                    contact_information=data.get('contact_information', ''),
                    date_of_birth=data.get('date_of_birth', '1970-01-01'),
                    emergency_contact=data.get('emergency_contact', ''),
                    insurance_id=data.get('insurance_id', ''),
                    medical_information=MedicalInformation.objects.create(history=''))

            patient.save()

            #log the patient creation
            log_event(request.user.username, 'c', 'p', patient.pk, 'all', 'emergency patient was created')

            #admit the new patient to the user's (medical professional's) hospital
            patient.admitted_to = hsptl
            patient.save()
            #log the admission as an emergency admission
            log_event(request.user.username, 'u', 'p', patient.pk, 'admitted_to', 'patient was admitted to ' + hsptl.name + ' with reason \"emergency\"')

        #send the user to the emergency registration success page
        return render(request, 'emergency_registration_complete.html', {'username': request.POST['username'], 'password': request.POST['password']})
