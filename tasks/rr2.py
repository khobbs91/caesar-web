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
import random
import sys
import logging
import tasks.random_routing as rr

print
print "testing assign_tasks for every member of 6.005 - Spring 2013"
print "number of chunks with at least 1 student line:", Chunk.objects.filter(student_lines__gte=1).count()
print "number of chunks by rcm:", Chunk.objects.filter(student_lines__gte=1, pk__in=Chunk.objects.filter(file__submission__authors__username='rcm')).count()
review_milestone = ReviewMilestone.objects.get(pk=2)
print "review milestone:",review_milestone
submit_milestone = review_milestone.submit_milestone
print "submit milestone:",submit_milestone
reviewers = list(User.objects.filter(membership__semester=review_milestone.assignment.semester))
random.shuffle(reviewers)
print "members of 6.005 - Spring 2013:",[r.username for r in reviewers]
print
num_chunks = 0;
for r in reviewers:
  role = str(Member.objects.get(user=r,semester=review_milestone.assignment.semester).get_role_display())
  num_tasks_to_assign = rr.num_tasks_for_user(review_milestone, r)
  print "reviewer:",r,"("+role+" - needs "+str(num_tasks_to_assign)+" chunks)"
  print "num reviewable chunks:",len(rr.get_reviewable_chunks(review_milestone, r))
  chunks_to_assign = rr.assign_tasks(review_milestone, r, tasks_to_assign=None, simulate=False)
  print "chunks assigned:",[c.id for c in chunks_to_assign]
  num_chunks+=len(chunks_to_assign)
  print
print "total number of chunks assigned:",num_chunks
