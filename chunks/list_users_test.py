from __future__ import division
from collections import namedtuple, defaultdict
import itertools
from random import shuffle
from django.db.models import Count
from django.contrib import auth
from django.contrib.auth.models import User
from django.db.models.query import prefetch_related_objects
from tasks.models import Task, app_settings
from chunks.models import Chunk, ReviewMilestone, SubmitMilestone, Assignment, Semester, Milestone, Submission, File, Subject, Semester
from accounts.models import Member
from review.models import Comment
import random
import sys
import logging
import tasks.random_routing as rr

# create a Subject
subject = Subject.objects.all()[1]
subject.name = "subject"
subject.pk = None
subject.save()
# create a Semester
semester = Semester(subject=subject, semester="semester")
semester.save()
# create a Assignment
assignment = Assignment(semester=semester, name="assignment")
assignment.save()
# create 300  users that will become members of the semester
users = User.objects.exclude(username__contains="user").order_by('?').all()
for i in range(300):
	u = users[i%20]
	u.pk = None
	u.username = "user"+str(100+i)
	u.save()
semester_members = User.objects.filter(username__contains="user").order_by('?').all()
# create a SubmitMilestone
submit_milestone = SubmitMilestone(assignment=assignment,name="submit_milestone")
submit_milestone.save()
# create a ReviewMilestone
review_milestone = ReviewMilestone(assignment=assignment,submit_milestone=submit_milestone,name="review_milestone")
review_milestone.save()

chunk_to_copy = Chunk.objects.filter(student_lines__gte=5)[0]
file_to_copy = chunk_to_copy.file
# make all the users members of the class
# create a Submission for every member in the class
for m in semester_members:
	roles = [Member.STUDENT, Member.STUDENT, Member.TEACHER, Member.VOLUNTEER]
	member = Member(semester=semester,user=m,role=roles[m.id%4])
	# member = Member(semester=semester,user=m,role=Member.STUDENT)
	member.save()
	m.membership.add(member)
	m.save()
	semester.members.add(member)
	semester.save()
	submission = Submission(milestone=submit_milestone,name="submission_"+m.username)
	submission.pk = None
	# submission.milestone_id = submit_milestone.id
	submission.save()
	submission.authors.add(m)
	submission.save()
	# create 8 files that each have 1 chunk
	for i in range(8):
		file = file_to_copy
		file.pk = None
		file.submission = submission
		file.chunks = []
		file.path = file.path + str(m.id) + "_" + str(i)
		file.submission_id = submission.id
		file.save()
		chunk = chunk_to_copy
		chunk.pk = None
		chunk.name = "chunk_"+m.username+str(i)
		chunk.file = file
		chunk.save()
		file.chunks.add(chunk)
		file.save()

for r in semester_members:
  rr.assign_tasks(review_milestone, r, tasks_to_assign=None, simulate=False)

# delete everything we created in our test
# subject.delete()