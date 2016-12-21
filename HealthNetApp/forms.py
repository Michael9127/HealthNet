"""
filename: forms.py
authors: Chris Lenter, Coleman Link, Mike Borkenstein, Rich Patulski, Sam Kilgore
purpose: the forms for the HealthNetApp application
"""

from django import forms

from django.forms import ModelForm, Textarea, ModelChoiceField, FileField
from .models import Patient, Hospital, MedicalInformation, Appointment, Doctor, Person, Prescription, Message, MedicalTest
from django.forms.widgets import FileInput
from django.core.exceptions import ValidationError

'''
Catch the exception thrown when creating a bad datetime (out of range,
e.g. year 9999) during clean() / is_valid() instead of later on.

This code is Chris' fault.
'''
import time, datetime


class RegisterForm(ModelForm):
    '''
    RegisterForm for a user registering an account
    Patients use this while doctors and nurses must be added via a system administrator
    '''
    password = forms.CharField(widget=forms.PasswordInput())
    cpassword = forms.CharField(widget=forms.PasswordInput(), label="Confirm password")

    email = forms.CharField()

    class Meta:
        model = Patient
        fields = ['name', 'username', 'date_of_birth', 'contact_information',
                  'preferred_hospital', 'insurance_id','emergency_contact']

        widgets = {
            'contact_information': Textarea(attrs={'rows': 5}),
            'emergency_contact': Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply form-control class to every element in order to
        # style with bootstrap
        for myField in self.fields:
            self.fields[myField].widget.attrs['class'] = 'form-control'

class StaffRegisterForm(ModelForm):
    '''
    Allows an administrator to create doctors, nurses, and other administrators.
    '''
    user_type = forms.ChoiceField(choices=[(0,"Administrator"), (1,"Doctor"), (2,"Nurse")])
    password = forms.CharField(widget=forms.PasswordInput())
    cpassword = forms.CharField(widget=forms.PasswordInput(), label="Confirm password")
    email = forms.CharField()
    hospital = forms.ModelChoiceField(Hospital.objects)

    class Meta:
        model = Person
        fields = ['name', 'username', 'date_of_birth', 'contact_information']
        widgets = {
            'contact_information': Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply form-control class to every element in order to style with bootstrap
        for myField in self.fields:
            self.fields[myField].widget.attrs['class'] = 'form-control'

class ProfileForm(ModelForm):
    '''
    ProfileForm for the Patient's profile information
    '''
    password = forms.CharField(widget=forms.PasswordInput(),
                               required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput(),
                               required=False)
    email = forms.CharField()
    date_of_birth = forms.DateField()
    date_of_birth.widget.attrs.update({'class': 'form-control'})
    class Meta:
        model = Patient
        fields = ['name', 'contact_information',
                  'preferred_hospital','insurance_id', 'emergency_contact']
        widgets = {
            'contact_information': Textarea(attrs={'rows': 5}),
            'emergency_contact': Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply form-control class to every element in order to
        # style with bootstrap
        for myField in self.fields:
            self.fields[myField].widget.attrs['class'] = 'form-control'



class PrescriptionForm(ModelForm):

    class Meta:
        model = Prescription

        fields = ['name', 'end_Date','usage']
        widgets = {
            'usage': Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply form-control class to every element in order to
        # style with bootstrap
        for myField in self.fields:
            self.fields[myField].widget.attrs['class'] = 'form-control'
            
class ValidatingDateField(forms.DateField):
    def clean(self, date):
        dt = None
        try:
            if date:
                dt = self.to_python(date)
                tt = (dt.year, dt.month, dt.day,
                0, 0, 0,
                dt.weekday(), 0, 0)
                stamp = time.mktime(tt)
        except Exception as e:
            raise ValidationError("Date out of range")
        return dt or date

forms.DateField = ValidatingDateField
            
class LoginForm(forms.Form):
    '''
    Login form for a user's login
    '''
    username = forms.CharField(label='Username',
                               max_length=30)
    password = forms.CharField(label='Password',
                               widget=forms.PasswordInput())

class MedicalInformationForm(ModelForm):
    '''
    Form to view MedicalInformation
    prescription and history CharFields are not required for complete form
    '''
    prescription = forms.CharField(required=False, max_length=500)
    history = forms.CharField(required=False, max_length=1000)
    tests = forms.CharField(required=False, max_length=1000)
    tests.widget=forms.Textarea(attrs={'rows': 5, 'placeholder':'Tests'})
    prescription.widget = forms.Textarea(attrs={'rows': 5, 'placeholder':'Prescriptions'})
    history.widget = forms.Textarea(attrs={'rows': 5, 'placeholder':'History', 'class': 'form-control'})
    class Meta:
        model = MedicalInformation
        fields = ['history', 'prescription', 'tests']


class AppointmentForm(forms.Form):
    # Disable the empty label "------"; i.e. force the user to choose a hospital
    hospital = ModelChoiceField(queryset=Hospital.objects, empty_label=None)
    hospital.widget.attrs.update({'class': 'form-control'})

    date = forms.DateField()
    date.widget.attrs.update({'class': 'form-control'})
    start_time = forms.TimeField()
    start_time.widget.attrs.update({'class': 'form-control'})
    end_time = forms.TimeField()
    end_time.widget.attrs.update({'class': 'form-control'})


    '''
    def clean_date(self):
        date = self.cleaned_data['date']
        start_time = time.time()
        try:
            validateDateTime(datetime.datetime.combine(date, datetime.time()))
        except:
            self._errors["date"] = ErrorList()
            self._errors["date"].append("Date out of range or date/time otherwise invalid")
            del self.cleaned_data["date"]
        return date
    '''


class PatientAppointmentForm(AppointmentForm):
    '''
    A form for patients - patients cannot sign up other users.
    '''
    doctor = ModelChoiceField(queryset=Doctor.objects, empty_label=None)
    doctor.widget.attrs.update({'class': 'form-control'})


class DoctorAppointmentForm(AppointmentForm):

    def __init__(self, *args, **kwargs):
        patient_list = kwargs.pop('patient_list')
        super(DoctorAppointmentForm, self).__init__(*args, **kwargs)
        self.fields['patient'].queryset = patient_list

    doctor = ModelChoiceField(queryset=Doctor.objects, empty_label=None)
    doctor.widget.attrs.update({'class': 'form-control'})
    patient = ModelChoiceField(queryset=Patient.objects.none(), empty_label=None)
    patient.widget.attrs.update({'class': 'form-control'})
    class Meta:
        model = Appointment
        fields = ['start', 'end', 'hospital']



class MedicalTestForm(ModelForm):
    pictures = forms.FileField(label='Upload a Picture', required=False,widget=FileInput)
    pictures1 = forms.FileField(label='Upload a Picture', required=False,widget=FileInput)
    pictures2 = forms.FileField(label='Upload a Picture', required=False,widget=FileInput)
    pictures3 = forms.FileField(label='Upload a Picture', required=False,widget=FileInput)
    #label is just a label/text, required = False makes it not a required field, widget thing removes annoying clear checkbox
    class Meta:
        model = MedicalTest
        fields = ['title','testDate', 'doctor','hospital', 'results', 'pictures', 'pictures1','pictures2','pictures3']
        widgets = {
            'usage': Textarea(attrs={'rows': 5}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply form-control class to every element in order to
        # style with bootstrap
        for myField in self.fields:
            self.fields[myField].widget.attrs['class'] = 'form-control'



class MessageForm(forms.Form):
    destination = ModelChoiceField(queryset=Person.objects, empty_label=None)
    destination.widget.attrs.update({'class': 'chosen-select'})
    subject = forms.CharField(label='Subject',max_length=100)
    body = forms.CharField(label='Body',max_length=1000, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply form-control class to every element in order to
        # style with bootstrap
        for myField in self.fields:
            self.fields[myField].widget.attrs['class'] = 'form-control'

class CustomDateForm(forms.Form):
    start = forms.DateField(required=False)
    start.widget.attrs.update({'class': 'form-control'})
    end = forms.DateField(required=False)
    end.widget.attrs.update({'class': 'form-control'})
