from __future__ import division
from collections import namedtuple, defaultdict
import itertools
from random import shuffle
from django.db.models import Count
from django.contrib import auth
from django.contrib.auth.models import User
from django.db.models.query import prefetch_related_objects
from tasks.models import Task, app_settings
from chunks.models import Chunk, ReviewMilestone, SubmitMilestone, Assignment, Semester, Milestone, Submission, File
from accounts.models import Member
from review.models import Comment
import random
import sys
import logging
import tasks.random_routing as rr

# creating a fake SubmitMilestone, ReviewMilestone, Submission, File, and 50 Chunks
assignment = Assignment.objects.all()[1]
semester = assignment.semester
semester_members = User.objects.filter(membership__semester=semester)

rr_submit_milestone = SubmitMilestone(assignment=assignment,name="rr3_submit_milestone")
rr_submit_milestone.save()
rr_review_milestone = ReviewMilestone(assignment=assignment,submit_milestone=rr_submit_milestone,name="rr3_review_milestone")
rr_review_milestone.save()

rr_chunks = []
chunk_to_copy = Chunk.objects.filter(student_lines__gte=5)[0]
file_to_copy = chunk_to_copy.file
# create a submission for every member in the class
for m in semester_members:
	rr_submission = Submission(milestone=rr_submit_milestone,name="rr3_submission_"+m.username)
	rr_submission.milestone_id = rr_submit_milestone.id
	rr_submission.save()
	rr_submission.authors.add(m)
	rr_file = file_to_copy
	rr_file.pk = None
	rr_file.submission = rr_submission
	rr_file.save()
	# every member in the class will submit 2 chunks
	for i in range(2):
		rr_chunk = chunk_to_copy
		rr_chunk.pk = None
		rr_chunk.name = "chunk_"+m.username+str(i)
		rr_chunk.file = rr_file
		rr_chunk.save()
		rr_file.chunks.add(rr_chunk)
		rr_chunks.append(rr_chunk)

for r in semester_members:
  rr.assign_tasks(rr_review_milestone, r, tasks_to_assign=None, simulate=False)

# delete everything we created in our test
# rr_submit_milestone.delete()