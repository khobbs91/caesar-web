from __future__ import division

from collections import namedtuple, defaultdict
import itertools
from random import shuffle

from django.db.models import Count
from django.contrib import auth
from django.contrib.auth.models import User
from django.db.models.query import prefetch_related_objects

from tasks.models import Task, app_settings
from chunks.models import Chunk, ReviewMilestone
from accounts.models import Member
import random
import sys
from django.db.models import Q
# import app_settings
import logging

__all__ = ['assign_tasks']

# filter all chunks to return only the ones that can be assigned to the reviewer
def get_reviewable_chunks(review_milestone, reviewer):
	# get the chunks for the milestone
	chunks = Chunk.objects.all()
	# remove chunks that aren't in this submit_milestone
	chunks = chunks.filter(file__submission__milestone=review_milestone.submit_milestone)
	# remove chunks already assigned to reviewer
	chunks = chunks.exclude(tasks__reviewer=reviewer)
	# remove chunks that have too few student-generated lines
	chunks = chunks.exclude(student_lines__lt=review_milestone.min_student_lines)
	# remove chunks that aren't selected for review
	chunks = chunks.exclude(name__in=list_chunks_to_exclude(review_milestone))
	# remove chunks that the reviewer authored
	chunks = chunks.exclude(pk__in=chunks.filter(file__submission__authors__id=reviewer.id))
	# remove chunks that already have enough reviewers of the same type (teacher, student, voluteer)
	chunks_enough_same_role_reviewers = get_chunks_with_enough_same_role_reviewers(chunks,review_milestone,reviewer)
	chunks = chunks.exclude(pk__in=chunks_enough_same_role_reviewers)
	# chunks = chunks.annotate(num_tasks=Count('tasks')).exclude(num_tasks__gte=num_tasks_for_user(review_milestone, reviewer))
	chunks = chunks.select_related('id','file__submission__id','file__submission__authors')
	chunks_enough_same_role_reviewers = chunks_enough_same_role_reviewers.select_related('id','file__submission__id','file__submission__authors')

	# concatenate the 2 lists (but make sure the chunks that need more same role reviewers list is first)
	# this is where I will test algorithms--I will order chunks in predefined orders instead of randomly
	chunks_list = order_chunks_random(chunks) + order_chunks_random(chunks_enough_same_role_reviewers)
	return chunks_list

# randomly order the chunks
def order_chunks_random(chunks):
	chunks_list = list(chunks)
	random.shuffle(chunks_list)
	return chunks_list

def assign_tasks(review_milestone, reviewer, tasks_to_assign=None, simulate=False):
	# check if tasks_to_assign == None. If true: set it to num required by milestone - num already assigned
	if tasks_to_assign == None:
		tasks_to_assign = num_tasks_for_user(review_milestone, reviewer)

	chunks = get_reviewable_chunks(review_milestone, reviewer)

	# take the first num_tasks_for_user chunks
	chunks_to_assign = chunks[:tasks_to_assign]
	# if len(chunks_to_assign) < num_tasks_for_user, the reviewer will be assigned fewer
	# tasks than they should be and they will be assigned more tasks the next time they
	# log in if there are more tasks they can be assigned

	if not simulate:
		# create tasks for the first tasks_to_assign chunks and save them
		for c in chunks_to_assign:
			task = Task(reviewer_id=reviewer.id, chunk_id=c.id, milestone=review_milestone, submission_id=c.file.submission.id)
			task.save()
	return chunks_to_assign

# this method ignores any tasks already in the database for this milestone
def simulate_tasks(review_milestone):
	reviewers = User.objects.filter(membership__semester=review_milestone.assignment.semester)
	reviewers_list = list(reviewers)
	random.shuffle(reviewers_list)
	chunk_id_task_map = {}
	user_id_task_map = {}
	for r in reviewers_list:
		chunks_to_assign = assign_tasks(review_milestone, r, tasks_to_assign=None, simulate=True)
		for c in chunks_to_assign:
			task = Task(reviewer_id=r.id, chunk_id=c.id, milestone=review_milestone, submission_id=c.file.submission.id)
			if c.id in chunk_id_task_map.keys():
				chunk_id_task_map[c.id] += [task]
			else:
				chunk_id_task_map[c.id] = [task]
	return chunk_id_task_map

# returns list of chunks that already have enough reviewers with the same role as reviewer
def get_chunks_with_enough_same_role_reviewers(chunks,review_milestone,reviewer):
	# get the reviewer's role
	reviewer_role = reviewer.membership.get(semester=review_milestone.assignment.semester).role
	# get all members with the same role in the class
	members_same_role = Member.objects.filter(semester=review_milestone.assignment.semester)
	if reviewer_role == Member.STUDENT or reviewer_role == Member.VOLUNTEER:
		members_same_role = members_same_role.filter(Q(role=Member.STUDENT)|Q(role=Member.VOLUNTEER))
	elif reviewer_role == Member.TEACHER:
		members_same_role = members_same_role.filter(role=Member.TEACHER)
	else:
		members_same_role = Member.objects.none()
	# get all tasks for chunks in this ReviewMilestone with reviewers that have the same role in the class
	tasks_same_role = Task.objects.filter(milestone=review_milestone).filter(reviewer__membership__pk__in=members_same_role)
	# aggregate tasks by the chunk they're for and count the number of tasks for each chunk
	tasks_same_role = tasks_same_role.values('chunk').annotate(Count('id'))
	# remove chunks that need more same role reviewers
	chunks_enough_same_role_tasks = tasks_same_role.filter(id__count__gte=num_tasks_for_role(review_milestone,reviewer_role)).values('chunk')
	# get all chunks that already have enough reviewers with the same role in the class
	chunks = chunks.filter(id__in=chunks_enough_same_role_tasks)
	return chunks

# return the maximum allowable number of tasks for a given role for a given chunk
# ex: chunks can only have 1 teacher reviewer
# ex: chunks can only have up to 2 student/volunteer reviewers
def num_tasks_for_role(review_milestone,role):
	if role == Member.STUDENT:
		num_role_per_chunk = review_milestone.reviewers_per_chunk
		# num_role_per_chunk = 2
	elif role == Member.TEACHER:
		# num_role_per_chunk = review_milestone.teacher_reviewers_per_chunk
		num_role_per_chunk = 1
	elif role == Member.VOLUNTEER:
		num_role_per_chunk = review_milestone.reviewers_per_chunk
		# num_role_per_chunk = 2
	return num_role_per_chunk

def num_tasks_for_user(review_milestone, user):
	member = Member.objects.get(user=user, semester=review_milestone.assignment.semester)
	# num_tasks_already_assigned = Task.objects.filter(reviewer=user, milestone=review_milestone).count()
	num_tasks_per_role = 0
	if member.role == Member.STUDENT:
		num_tasks_per_role = review_milestone.student_count
	elif member.role == Member.TEACHER:
		num_tasks_per_role = review_milestone.staff_count
	elif member.role == Member.VOLUNTEER:
		num_tasks_per_role = review_milestone.alum_count
	else:
		num_tasks_per_role = 0
	# return min(0,num_tasks_per_role - num_tasks_already_assigned)
	return num_tasks_per_role

def list_chunks_to_exclude(review_milestone):
	to_exclude = review_milestone.chunks_to_exclude
	if to_exclude == None:
		return []
	return to_exclude.split(",")