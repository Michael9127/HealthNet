from django.conf.urls import url
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^register/$', views.register, name='register'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^login/?$', views.login, name='login'), # optional trailing slash to make ?next work (redirect from @login_required)
    url(r'^updatepatient/$', views.updatePatient, name='updatepatient'),
    url(r'^listpatients/$', views.listPatients, name='listpatients'),
    url(r'^calendar/$', views.calendar, name='Calendar'),
    url(r'^updatepatient/(?P<patient_pk>\d+)/$', views.updatePatientMedicalInformation,
        name='updatepatientmedicalinformation'),
    url(r'^updateappointment/(?P<appointment_pk>\d+)/$', views.update_appointment,
        name='update_appointment'),
    url(r'^createappointment/$', views.create_appointment, name='createappointment'),
    url(r'^cancelappointment/(?P<appointment_pk>\d+)/$', views.cancel_appointment,
        name='cancel_appointment'),
    url(r'^view_logs/$', views.view_logs, name='view_logs'),
    url(r'^view_logs/(?P<person_pk>\d+)/$', views.view_logs_by_user, name='view_logs_by_user'),
    url(r'^view_log_entry/(?P<log_entry_pk>\d+)/$', views.view_log_entry, name='view_log_entry'),
    url(r'^register_staff/$', views.register_staff, name='register_staff'),
    url(r'^listmessages/$', views.list_messages, name='listmessages'),
    url(r'^viewmessage/(?P<messageID>\d+)/$', views.view_message, name='viewmessage'),
    url(r'^sendmessage/$', views.send_message, name='sendmessage'),
    url(r'^reply/(?P<message_pk>\d+)/$', views.reply, name='reply'),
    url(r'^listTests/(?P<patient_pk>\d+)/$', views.listTests, name='listTests'),
    url(r'^removeTest/(?P<patient_pk>\d+)/(?P<test_pk>\d+)/$', views.removeTest, name='removeTest'),
    url(r'^receiveMedicalTest/(?P<patient_pk>\d+)/$', views.receiveMedicalTest, name='receiveMedicalTest'),
    url(r'^getTestForm/(?P<patient_pk>\d+)/$', views.getTestForm, name='getTestForm'),
    url(r'^viewTestForm/(?P<test_pk>\d+)/(?P<edit>\d+)/$', views.viewTestForm, name='viewTestForm'),
    url(r'^confirmTest/(?P<test_pk>\d+)/(?P<patient_pk>\d+)/$', views.confirmTest, name='confirmTest'),
    url(r'^editTest/(?P<test_pk>\d+)/$', views.editTest, name='editTest'),
    url(r'^export/$', views.exportInformation, name='export'),
    url(r'^listPrescriptions/(?P<patient_pk>\d+)/$', views.listPrescriptions, name='listPrescriptions'),
    url(r'^deletePrescription/(?P<patient_pk>\d+)/(?P<prescription_pk>\d+)/$', views.deletePrescription,
        name='deletePrescription'),
    url(r'^getPrescriptionForm/(?P<patient_pk>\d+)/$', views.getPrescriptionForm, name='getPrescriptionForm'),
    url(r'^acceptPrescriptionForm/(?P<patient_pk>\d+)/$', views.acceptPrescriptionForm, name='acceptPrescriptionForm'),
    url(r'^admit_patient/(?P<patient_pk>\d+)/$', views.admitPatient, name='admit_patient'),
    url(r'^d3Statistics/$', views.d3Statistics, name='Statistics'),
    url(r'^statisticscategories/$', views.system_statistics_categories, name='statisticscategories'),
    url(r'^viewstatistics/$', views.system_statistics, name='viewstatistics'),
    url(r'^emergencyregistration/$', views.emergency_register_patient, name='emergencyregistration'),
]
urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
