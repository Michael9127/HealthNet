Installation Instructions:
	In order to run this HealthNet program, given a zip file containing its code, do the following:
		1. Make sure the target machine has the prerequisites (python 3.4.3 and django 1.9.1) installed.
		2. Unzip the source code from the zip file into the desired installation location on the target machine.
		3. HealthNet has now been installed, to run the system navigate into the HealthNetProject directory
			in a terminal and run the command `python manage.py runserver`


Prerequisites:
	python version 3.4.3
	django version 1.9.1


Known Bugs and Disclaimers:
	There are no known bugs within the system.


Known Missing Release 2 Features:
	All release 2 features are present within the system.


Usage Instructions:
	1. Run `python manage.py runserver` from the HealthNetProject/ directory.
	2. Open your favorite modern day web browser.
	3. Navigate to the url: http://localhost:8000/
	4. You have reached the health net login page, and can make use of the system.
	5. Below are the various types of users within the system, and the functionality
		available to each of them:


	Format:
		User Type:
			username for example user of this type
			password for example user of this type



	Superuser/Administrator:
		admin
		adminpasswd

	Administrators can create hospitals via the "Database" link in the top navigation bar.
	Administrators can create delete log entries via the "Database" link in the top navigation bar.
	Administrators can register other staff members (doctors, nurses, and administrators),
		view system logs, view logging and general system statistics, list all the
		patients and appointments within the system, and view and send messages, all
		using the links within the navigation bar at the top of the page.



	Doctor:
		doc
		what'supdoc

	Doctors can see a list of all patients of HealthNet (at http://127.0.0.1:8000/listpatients/)
		and navigate to any patient's medical information page from their name in the list.
		The patient list is also searchable (by patient name) via the bar at the top.
	Doctors can see all of the appointments that they have with patients, also create and delete appointments as well.
	Doctors can add prescriptions and medical tests for each patient, and release the results for each test.
	Doctors get a Patient List from which they can create, read, update, and delete prescriptions, from the links
		on an individual patient's page.
	Doctors can also admit, discharge, or transfer patients.



	Patient:
		krutzmeister
		a

	Patients can register to be a part of healthnet via http://localhost:8000/register/
	Patients can login via http://localhost:8000/app/login
	Patients can update their profile information via http://127.0.0.1:8000/app/updatepatient/
	Patients can create, view, and delete appointments from http://localhost:8000/calendar/



	Nurse:
		Nancy
		a

	Nurses can login via http://localhost:8000/app/login
	Nurses can set up an appointment and view them from http://localhost:8000/calendar/ 
	Nurses can see any appointments for their hospital, up to a week in advance.
