from django.test import TestCase
from .models import Person, Hospital,Patient,MedicalProfessional \
    ,Doctor, Nurse,Appointment, MedicalInformation
import datetime

class testPerson(TestCase):
    """
    testing the Person model
    """
    def setUp(self):
        Person.objects.create(name="Dave",
                              date_of_birth="1990-04-01",
                              contact_information="none",
                              username="Damnnn")
        #this is a valid creation
        Person.objects.create(name="Bill",
                              date_of_birth="2017-05-01",
                              contact_information="none",
                              username="Billius")

        #has birth date in future
        Person.objects.create(name="Daviel",
                              date_of_birth="1990-05-06",
                              contact_information="none",
                              username="Damnnn")
        #has same username as first person (Dave)
        Person.objects.create(name="David",
                              date_of_birth="1800-05-06",
                              contact_information="none",
                              username="Damnnn")
        #birth date is too far in the past

    #makeMyPeeps()
    def test_username_is_taken(self):
        dave = Person.objects.get(name="Dave")
        daviel = Person.objects.get(name="Daviel")
        #these two have the same username
        self.assertEqual(dave.username,daviel.username)

    def test_birthdate_is_in_future(self):
        inFuture=0
        for peep in Person.objects.all():
            if(peep.date_of_birth >datetime.date.today()):
                inFuture+=1
        #only one user has birthday in the future
        self.assertEqual(inFuture,1)

    def test_too_old(self):
        tooOld=0
        for peep in Person.objects.all():
            if(int(peep.date_of_birth.year) +150<int(datetime.date.today().year)):
                tooOld+=1
        #only one user is too old
        self.assertEqual(tooOld,1)


class testMedicalInformation(TestCase):
    def setUp(self):
        MedicalInformation.objects.create(history = "none yet")

    def test_something(self):
        self.assertEqual(1,1)



class testHospital(TestCase):
    def setUp(self):
        Hospital.objects.create(name="HealthNet Central")

    def test_hospital_name(self):
        hospital=Hospital.objects.get(name="HealthNet Central")
        self.assertEqual(hospital.name,"HealthNet Central")



class testPatient(TestCase):
    hosp = Hospital.objects.create(name="testHosp")
    medInfo = MedicalInformation.objects.create(history="none yet")
    def setUp(self):
        hosp = Hospital.objects.create(name="testHosp")
        medInfo = MedicalInformation.objects.create(history="none yet")
        Patient.objects.create(name="Bill",
                               date_of_birth="1985-01-01",
                               contact_information="phone",
                               username="Billium",
                               preferred_hospital=hosp,
                               admitted_to=hosp,
                               insurance_id=0,
                               medical_information=medInfo,
                               emergency_contact="mommy")
    def test_registration(self):
        pat = Patient.objects.get(username="Billium")
        hosp = Hospital.objects.get(name="testHosp")
        medInfo = MedicalInformation.objects.get(history="none yet")
        self.assertEqual(pat.preferred_hospital, hosp)
        self.assertEqual(pat.admitted_to, hosp)
        self.assertEqual(pat.emergency_contact, "mommy")
        #dummy checks basically
    #testing appts later
    """
    #todo:make test for can_create_appointment
    def test_list_appointments(self):
        pat = Patient.objects.get(name="Bill")
        now = datetime.datetime.now()

        start = now + datetime.timedelta(days=1)#appt starting tomorrow
        print("Start datetime: ", start)
        end = start + datetime.timedelta(hours=1)#appt goes for 1 hour
        print("end datetime: ", end)

        print("format for now(): ",datetime.datetime.now())
        appt = Appointment.objects.create(start=start,end = end)
        for appt in pat.list_appointments():
            self.assertEqual(appt.patient.username!=pat.username)
    def test_can_create_appointment(selfself):
        pass
    """


class testMedicalProfessional(TestCase):
    def setUp(self):
        Hospital.objects.create(name="HealthNet")
        hosp1=Hospital.objects.get(name="HealthNet")
        MedicalProfessional.objects.create(name="Bill",
                                            date_of_birth="1985-01-01",
                                            contact_information="phone",
                                            username="Billium",
                                            hospital=hosp1)



    def test_list_things(self):
        medProf=MedicalProfessional.objects.get(name="Bill")
        try:
            medProf.list_patients()
        except NotImplementedError:
            self.assertEqual(True,True)
        else: self.assertEqual(True,False)
        try:
            medProf.list_appointments()
        except NotImplementedError:
            self.assertEqual(True,True)
        else: self.assertEqual(True,False)

class testNurse(TestCase):
    def setUp(self):
        hosp1= Hospital.objects.create(name="HealthNet")
        hosp = Hospital.objects.create(name="testHosp")
        medInfo = MedicalInformation.objects.create(history="none yet")
        Nurse.objects.create(name="Bill1",
                                date_of_birth="1985-01-01",
                                contact_information="phone",
                                username="Billium1",
                                hospital=hosp1)
        Nurse.objects.create(name="Bill2",
                                date_of_birth="1985-01-01",
                                contact_information="something",
                                username="Billium2",
                                hospital=hosp)
        #two doctors from different hospitals
        Patient.objects.create(name="Bill",
                               date_of_birth="1985-01-01",
                               contact_information="phone",
                               username="Billius1",
                               preferred_hospital=hosp1,
                               admitted_to=hosp1,
                               insurance_id=0,
                               medical_information=medInfo,
                               emergency_contact="mommy")
        Patient.objects.create(name="Bill",
                               date_of_birth="1985-01-01",
                               contact_information="phone",
                               username="Billius2",
                               preferred_hospital=hosp,
                               admitted_to=hosp,
                               insurance_id=0,
                               medical_information=medInfo,
                               emergency_contact="mommy")
        #two patients going to 2 different hospitals
        #Patient:Billius1 ---> Nurse: Billium1
        #Patient:Billius2 ---> Nurse: Billium2

    def test_list_patients(self):
        nurse1 = Nurse.objects.get(username="Billium1")
        nurse2 = Nurse.objects.get(username="Billium2")
        pat1 = Patient.objects.get(username="Billius1")
        pat2 = Patient.objects.get(username="Billius2")
        list_pats1 = nurse1.list_patients()#should just get Billius1
        self.assertEqual(list_pats1[0], pat1)
        list_pats2 = nurse2.list_patients()#should just get Billius2
        self.assertEqual(list_pats2[0], pat2)
        #todo:have to make a bunch of patients
        #patients and test the list function
    """
    def test_list_appointments(self):
        self.assertEqual(True,True)
        #todo:have to make a bunch of appointments
        #appointments and test the list function
    """

"""
class testDoctor(TestCase):
    def makeNurse(self):
        Hospital.objects.create(name="HealthNet")
        hosp1=Hospital.objects.get(name="HealthNet")
        Doctor.objects.create(name="Bill",
                            date_of_birth="01/01/1985",
                            contact_information="phone",
                            username="Billium",
                            hospital=hosp1)
    def test_list_patients(self):
        self.assertEqual(True,True)
        #todo:actually Test this
    def test_list_appointments(self):
        self.assertEqual(True,True)
        #todo:same
"""

"""
class testAppointment(TestCase):
    def makeAppointments(self):
        start = datetime.datetime.now()
        start.replace(hour=12, minute=0, second=0, microsecond=0)
        start+=datetime.timedelta(days=5)
        end=datetime.datetime.now()
        end.replace(hour=13, minute=0, second=0, microsecond=0)
        end+=datetime.timedelta(days=5)
        Hospital.objects.create(name="HealthNet")
        hosp1=Hospital.objects.get(name="HealthNet")
        Doctor.objects.create(name="Bill",
                            date_of_birth="01/01/1985",
                            contact_information="phone",
                            username="Billium1",
                            hospital=hosp1)
        doc=Doctor.objects.get(username="Billium1")
        Doctor.objects.create(name="Billy",
                            date_of_birth="01/01/1985",
                            contact_information="phone",
                            username="Billium2",
                            hospital=hosp1)
        doc2=Doctor.objects.get(username="Billium2")
        Patient.objects.create(name="John",
                               date_of_birth="01/01/1985",
                               contact_information="phone",
                               username="Johnny",
                               emergency_contact="mommy")
        patty = Patient.objects.get(username="Johnny")
        Appointment.objects.create(start=start,
                                   end=end,
                                   doctor=doc,
                                   hospital=hosp1,
                                   patient=patty)
        start2 = datetime.datetime.now()
        start2.replace(hour=12, minute=30, second=0, microsecond=0)
        start2+=datetime.timedelta(days=5)
        end2=datetime.datetime.now()
        end2.replace(hour=13, minute=0, second=0, microsecond=0)
        end2+=datetime.timedelta(days=5)
        Appointment.objects.create(start=start2,
                                   end=end2,
                                   doctor=doc,
                                   hospital=hosp1,
                                   patient=patty)
        Appointment.objects.create(start=start2,
                                   end=end2,
                                   doctor=doc2,
                                   hospital=hosp1,
                                   patient=patty)

    def test_conflicts_same_user_or_doctor(self):
        appt1 = Appointment.objects.get(doctor="doc")
        appt2 = Appointment.objects.get(doctor="doc2")
        #todo:these are at the same time, so they still do conflict
        #need to make them different appointment times
        #there are also two appointments with same doctor as doc
        self.assertEqual(appt1.conflicts(appt1,appt2),False)
    def test_conflicts_times_and_timeErrors(self):
        appt1 = Appointment.objects.get(doctor="doc")
        #todo:there are two appointment objects with doctor doc
        appt2 = Appointment.objects.get(doctor="doc2")
        self.assertEqual(appt1.conflicts(appt1,appt2),True)
        self.assertEquals(appt1.time_errors(appt1),False)
        #todo:come up with an appointment that will come up as invalid
"""""