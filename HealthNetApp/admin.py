from django.contrib import admin
from .models import Patient, Hospital, LogEntry, MedicalInformation, Doctor, Appointment, Nurse, Message, Person, Administrator, MedicalProfessional, MedicalTest, Prescription

#admin.site.site_header = 'HealthNet'
admin.site.register(Patient)
admin.site.register(Hospital)
admin.site.register(LogEntry)
admin.site.register(Doctor)
admin.site.register(Nurse)
admin.site.register(Administrator)
