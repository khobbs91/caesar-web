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
user_in_class = semester_members[0]

semester_non_members = User.objects.exclude(pk__in=semester_members)
user_not_in_class = semester_non_members[0]
rr_submit_milestone = SubmitMilestone(assignment=assignment,name="rr3_submit_milestone")
rr_submit_milestone.save()
rr_review_milestone = ReviewMilestone(assignment=assignment,submit_milestone=rr_submit_milestone,name="rr3_review_milestone")
rr_review_milestone.save()
rr_submission = Submission(milestone=rr_submit_milestone,name="rr3_submission")
rr_submission.milestone_id = rr_submit_milestone.id
rr_submission.save()
rr_submission.authors.add(user_not_in_class)
rr_file = Chunk.objects.filter(student_lines__gte=5)[0].file
rr_file.pk = None
rr_file.submission = rr_submission
rr_file.save()
rr_chunks = []
for i in range(1):
	rr_chunk = Chunk.objects.filter(student_lines__gte=5)[0]
	rr_chunk.pk = None
	rr_chunk.name = "chunk_"+str(i)
	rr_chunk.file = rr_file
	rr_chunk.save()
	rr_file.chunks.add(rr_chunk)
	rr_chunks.append(rr_chunk)

# add enough tasks so that no one else will be assigned to the chunk
student1 = Member.objects.filter(semester=assignment.semester).filter(role='S')[0]
student2 = Member.objects.filter(semester=assignment.semester).filter(role='S')[1]
teacher1 = Member.objects.filter(semester=assignment.semester).filter(role='T')[0]
rr_task1 = Task(submission=rr_submission,reviewer=student1.user,chunk=rr_chunks[0],milestone=rr_review_milestone)
rr_task2 = Task(submission=rr_submission,reviewer=student2.user,chunk=rr_chunks[0],milestone=rr_review_milestone)
rr_task3 = Task(submission=rr_submission,reviewer=teacher1.user,chunk=rr_chunks[0],milestone=rr_review_milestone)
rr_task1.save()
rr_task2.save()
rr_task3.save()

# There are 50 chunks that are a part of the fake SubmitMilestone
print "num chunks in caesar               :",Chunk.objects.count()
# None of the chunks are assigned to any reviewers
# None of the chunks have too few student lines
# None of the chunks are excluded from the review process
# None of the chunks were authored by anyone in the class
print "num chunks in fake SubmitMilestone :",Chunk.objects.filter(file__submission__milestone=rr_submit_milestone).count()
# All 50 chunks are reviewable by ANY reviewer in the class
print "num chunks reviewable by",user_in_class.username," :",len(rr.get_reviewable_chunks(rr_review_milestone, user_in_class))
print

# If I run the routing algorithm for one student in the class
print "assigning chunks to",user_in_class.username,"..."
assigned_chunks = rr.assign_tasks(rr_review_milestone,user_in_class,simulate=True)
rr_tasks = [Task(reviewer_id=user_in_class.id,chunk_id=c.id,milestone=rr_review_milestone,submission_id=c.file.submission.id) for c in assigned_chunks]
[t.save() for t in rr_tasks]
print "chunks assigned to",user_in_class.username,"       :",[c.id for c in assigned_chunks]
print

# Now 0 chunks are reviewable by the same reviewer
print "num chunks reviewable by",user_in_class.username," :",len(rr.get_reviewable_chunks(rr_review_milestone, user_in_class))
# If I run the routing algorithm again for the same student
print "assigning chunks to",user_in_class.username,"..."
assigned_chunks = rr.assign_tasks(rr_review_milestone,user_in_class,simulate=True)
rr_tasks2 = [Task(reviewer_id=user_in_class.id,chunk_id=c.id,milestone=rr_review_milestone,submission_id=c.file.submission.id) for c in assigned_chunks]
[t.save() for t in rr_tasks2]
print "chunks assigned to",user_in_class.username,"       :",[c.id for c in assigned_chunks]
print

# deleting all tasks assigned to the same reviewer
print "deleting all tasks assigned to polovoco..."
[t.delete() for t in rr_tasks]
[t.delete() for t in rr_tasks2]
# Now all 50 chunks are reviewable by the same reviewer
print "num chunks reviewable by",user_in_class.username," :",len(rr.get_reviewable_chunks(rr_review_milestone, user_in_class))
print

# creating a chunk with too few student lines to be assigned
print "creating a chunk with too few student lines to be assigned..."
rr_chunk_lines = Chunk.objects.filter(student_lines__lt=5)[0]
rr_chunk_lines.pk = None
rr_chunk_lines.name = "chunk_not_enough_lines"
rr_chunk_lines.file = rr_file
rr_chunk_lines.save()
rr_file.chunks.add(rr_chunk_lines)
rr_chunks.append(rr_chunk_lines)
# Now there are 51 chunks in the fake SubmitMilestone
print "num chunks in fake SubmitMilestone :",Chunk.objects.filter(file__submission__milestone=rr_submit_milestone).count()
# But only 51 chunks are reviewable by ANY reviewer in the class
print "num chunks reviewable by",user_in_class.username," :",len(rr.get_reviewable_chunks(rr_review_milestone, user_in_class))
print

# creating a chunk authored by the reviewer who is a member of the class
print "creating a chunk authored by the reviewer in the class"
rr_submission2 = Submission(milestone=rr_submit_milestone,name="rr3_submission")
rr_submission2.milestone_id = rr_submit_milestone.id
rr_submission2.save()
rr_submission2.authors.add(user_in_class)
rr_file2 = Chunk.objects.filter(student_lines__gte=5, file__submission__authors=user_in_class.id)[0].file
rr_file2.pk = None
rr_file2.submission = rr_submission2
rr_file2.save()
rr_chunk = Chunk.objects.filter(student_lines__gte=5, file__submission__authors=user_in_class.id)[0]
rr_chunk.pk = None
rr_chunk.name = "chunk_by_polovoco"
rr_chunk.file = rr_file2
rr_chunk.save()
rr_file2.chunks.add(rr_chunk)
rr_chunks.append(rr_chunk)
# Now there are 52 chunks in the fake SubmitMilestone
print "num chunks in fake SubmitMilestone :",Chunk.objects.filter(file__submission__milestone=rr_submit_milestone).count()
# But only 50 chunks are reviewable by out reviewer
print "num chunks reviewable by",user_in_class.username," :",len(rr.get_reviewable_chunks(rr_review_milestone, user_in_class))
print

# deleting all the models we created in our test
rr_submit_milestone.delete()
# rr_submission.delete()
# rr_submission2.delete()
# rr_file.delete()
# rr_file2.delete()
# [c.delete() for c in rr_chunks]
# rr_task1.delete()
# rr_task2.delete()
# rr_task3.delete()

# chunk_id_task_map = rr.simulate_tasks(review_milestone)
# sum = 0
# for c in chunk_id_task_map.keys():
#   print c
#   print chunk_id_task_map[c]
#   sum += len(chunk_id_task_map[c])
#   print
# print "number of tasks assigned:" , sum
# print len(chunk_id_task_map.keys())