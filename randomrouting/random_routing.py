from __future__ import division

from collections import namedtuple, defaultdict
from itertools import chain
from random import shuffle

from django.db.models import Count
from django.contrib import auth
from django.contrib.auth.models import User
from django.db.models.query import prefetch_related_objects
from django.utils.datastructures import SortedDict

from tasks.models import Task, app_settings
from chunks.models import Chunk, ReviewMilestone
from accounts.models import Member
import random
import sys
from django.db.models import Q
# import app_settings
import logging
import copy

__all__ = ['assign_tasks']

# filter all chunks to return only the ones that can be assigned to the reviewer
def get_reviewable_chunks(review_milestone, reviewer, reviewer_role, simulate=False, chunk_id_task_map={}):
	reviewer_id = reviewer['id'] if simulate else reviewer.id
	# # get the chunks for the milestone
	# chunks = Chunk.objects.all()
	# # remove chunks that aren't in this submit_milestone
	# chunks = chunks.filter(file__submission__milestone=review_milestone.submit_milestone)
	# # remove chunks that have too few student-generated lines
	# chunks = chunks.exclude(student_lines__lt=review_milestone.min_student_lines)
	# # remove chunks that aren't selected for review
	# chunks = chunks.exclude(name__in=list_chunks_to_exclude(review_milestone))
	# # remove chunks already assigned to reviewer
	# chunks = chunks.exclude(tasks__reviewer__id=reviewer_id)
	# # chunks = chunks.exclude(id__in=chunks.filter(tasks__reviewer__id=reviewer_id))
	# # calling exclude directly takes 12 sec versus filtering and then excluding which takes 40 ms
	# # remove chunks that the reviewer authored
	# chunks = chunks.exclude(file__submission__authors__id=reviewer_id)
	# # chunks = chunks.exclude(id__in=chunks.filter(file__submission__authors__id=reviewer_id))
	
	# # get chunks that already have enough reviewers of the same type (teacher, student, voluteer)
	# chunks_enough_same_role_reviewers = get_chunks_with_enough_same_role_reviewers(chunks,review_milestone,reviewer,simulate=simulate,chunk_id_task_map=chunk_id_task_map)
	# # remove chunks that already have enough reviewers of the same type
	# chunks = chunks.exclude(pk__in=chunks_enough_same_role_reviewers)
	# # chunks = chunks.select_related('file__submission').prefetch_related('file__submission__authors')
	# chunks = chunks.values('id','name','file__submission__id')
	# chunks_enough_same_role_reviewers = chunks_enough_same_role_reviewers.values('id','name','file__submission__id')
	# return {'chunks_enough_same_role_reviewers':chunks_enough_same_role_reviewers,'chunks_not_enough_same_role_reviewers':chunks}

	# reviewer_role_display = dict(Member.ROLE_CHOICES).get(reviewer_role)
	num_role_tasks = get_num_tasks_for_role(review_milestone,reviewer_role)
	# putting everything inside a single filter as a test
	chunks = Chunk.objects.filter(file__submission__milestone=review_milestone.submit_milestone).exclude(student_lines__lt=review_milestone.min_student_lines, name__in=list_chunks_to_exclude(review_milestone), tasks__reviewer__id=reviewer_id, file__submission__authors__id=reviewer_id)
	if reviewer_role == Member.STUDENT or reviewer_role == Member.VOLUNTEER:
		chunks = chunks.filter(chunk_review__student_alum_reviewers__lt=num_role_tasks)
		chunks_enough_same_role_reviewers = chunks.filter(chunk_review__student_alum_reviewers__gte=num_role_tasks)
	elif reviewer_role == Member.TEACHER:
		chunks = chunks.filter(chunk_review__staff_reviewers__lt=num_role_tasks)
		chunks_enough_same_role_reviewers = chunks.filter(chunk_review__staff_reviewers__gte=num_role_tasks)
	else:
		chunks_enough_same_role_reviewers = chunks
		chunks = Chunk.objects.none()
	chunks = chunks.values('id','name','file__submission__id')
	chunks_enough_same_role_reviewers = chunks_enough_same_role_reviewers.values('id','name','file__submission__id')
	return {'chunks_enough_same_role_reviewers':chunks_enough_same_role_reviewers,'chunks_not_enough_same_role_reviewers':chunks}

# this is where I will test algorithms--I will order chunks in predefined orders instead of randomly
def apply_routing_algorithm(chunks, tasks_to_assign, routing_algorithm='random'):
	algo = routing_algorithms.get(routing_algorithm)
	# apply the routing algorithm to both querysets in chunks & limit the results to tasks_to_assign
	chunks_not_enough_same_role_reviewers = algo(chunks['chunks_not_enough_same_role_reviewers'])[:tasks_to_assign]
	chunks_enough_same_role_reviewers = algo(chunks['chunks_enough_same_role_reviewers'])[:tasks_to_assign]
	# concatenate the two querysets together (put the chunks that need more same role reviewers are first)
	# chunks_list = chunks_not_enough_same_role_reviewers + chunks_enough_same_role_reviewers
	chunks_list = list(chain(chunks_not_enough_same_role_reviewers, chunks_enough_same_role_reviewers))
	# get the first num_tasks_for_user chunks to assign to the reviewer
	return chunks_list[:tasks_to_assign]

# randomly order the chunks
def routing_algorithm_random(chunks):
	return chunks.order_by('?')

# order the chunks by id
def routing_algorithm_ordered_id(chunks):
	return chunks.order_by('id')

# dictionary containing all possible routing algorithms
routing_algorithms = {'random':routing_algorithm_random,'ordered':routing_algorithm_ordered_id}

def assign_tasks(review_milestone, reviewer, routing_algorithm='random', tasks_to_assign=None, simulate=False, chunk_id_task_map={}):
	# if tasks_to_assign == None, set tasks_to_assign equal to number required by the milestone for the reviewer's role
	if tasks_to_assign == None:
		tasks_to_assign = get_num_tasks_for_user(review_milestone, reviewer, simulate=simulate)
	reviewer_role = None
	if simulate:
		reviewer_role = reviewer['membership__role']
	else:
		reviewer_role = reviewer.membership.get(semester=review_milestone.assignment.semester).role
	# get all the chunks that the reviewer can review in the order they should be assigned
	reviewable_chunks = get_reviewable_chunks(review_milestone, reviewer, reviewer_role, simulate=simulate, chunk_id_task_map=chunk_id_task_map)
	chunks_to_assign = apply_routing_algorithm(reviewable_chunks, tasks_to_assign, routing_algorithm=routing_algorithm)
	# if len(chunks_to_assign) < num_tasks_for_user, the reviewer will be assigned fewer
	# tasks than they should be and they will be assigned more tasks the next time they
	# log in if there are more tasks they can be assigned

	# create and save tasks if it's NOT a simulation
	if not simulate:
		# create tasks for the chunks in chunks_to_assign and save them
		for chunk in chunks_to_assign:
			task = Task(reviewer_id=reviewer.id, chunk_id=chunk['id'], milestone=review_milestone, submission_id=chunk['file__submission__id'])
			task.save()
			chunk.chunk_review.add_reviewer_id(reviewer.id)
			if reviewer_role == Member.STUDENT:
				chunk.chunk_review.student_reviewers += 1
				chunk.chunk_review.student_alum_reviewers += 1
			elif reviewer_role == Member.VOLUNTEER:
				chunk.chunk_review.alum_reviewers += 1
				chunk.chunk_review.student_alum_reviewers += 1
			elif reviewer_role == Member.TEACHER:
				chunk.chunk_review.staff_reviewers += 1
	return chunks_to_assign

# TODO: use len(list) and queryset.count() because len will evaluate a queryset
# TODO: prefetch_related('assignment__semester') for review_milestone
# this method ignores any tasks already in the database for this milestone
def simulate_tasks(review_milestone, routing_algorithm='random'):
	semester = review_milestone.assignment.semester
	# create a dictionary to translate Member roles (S,T,V) into words (student, teacher, volunteer)
	member_roles = dict(Member.ROLE_CHOICES)
	# create a dictionary to keep track of the tasks assigned to each chunk
	chunk_id_task_map = {}
	tasks = SortedDict()
	tasks['student'] = []
	tasks['volunteer'] = []
	tasks['teacher'] = []
	tasks['nonmember'] = []
	# get all the potential reviewers in the semester
	reviewers = User.objects.filter(membership__semester=semester)
	# prefetch related membership and semester objects for every potential reviewer
	# reviewers = reviewers.prefetch_related('membership__semester')
	reviewers = reviewers.values('id','username','membership__role','membership__semester__id').order_by('?').distinct()
	# randomly order all the potential reviewers
	# reviewers = reviewers.order_by('?')
	# iterate through potential reviewers and assign them tasks
	for reviewer in reviewers:
		# only look at the reviewer instance if their membership is for this semester
		if reviewer['membership__semester__id'] == semester.id:
			# get the reviewer's role
			# reviewer_role_display = member_roles.get(reviewer.membership.get(semester=review_milestone.assignment.semester).role)
			# reviewer_role_display = member_roles.get(reviewer.membership.get(semester=review_milestone.assignment.semester).role)
			reviewer_role_display = member_roles.get(reviewer['membership__role'])
			# get the chunks to assign to the reviewer
			chunks_to_assign = assign_tasks(review_milestone, reviewer, routing_algorithm=routing_algorithm, tasks_to_assign=None, simulate=True, chunk_id_task_map=chunk_id_task_map)
			# tasks = []
			for chunk in chunks_to_assign:
				# task = Task(reviewer_id=reviewer.id, chunk_id=chunk['id'], milestone=review_milestone, submission_id=chunk['file__submission__id'])
				if chunk['id'] not in chunk_id_task_map.keys():
					chunk_id_task_map[chunk['id']] = {'chunk':chunk,'tasks':copy.deepcopy(tasks)}
				current_reviewers = chunk_id_task_map[chunk['id']]['tasks'][reviewer_role_display]
				chunk_id_task_map[chunk['id']]['tasks'][reviewer_role_display] = current_reviewers + [{'username':reviewer['username'],'id':reviewer['id']}]
				# chunk_id_task_map[chunk['id']]['tasks'][reviewer_role_display].append(reviewer)
	return chunk_id_task_map

# returns list of chunks that already have enough reviewers with the same role as reviewer
def get_chunks_with_enough_same_role_reviewers(chunks,review_milestone,reviewer,simulate=False,chunk_id_task_map={}):
	member_roles = dict(Member.ROLE_CHOICES)
	# get the reviewer's role
	reviewer_role = None
	reviewer_role_display = None
	if simulate:
		reviewer_role = reviewer['membership__role']
		reviewer_role_display = member_roles.get(reviewer['membership__role'])
	else:
		reviewer_role = reviewer.membership.get(semester=review_milestone.assignment.semester).role
		reviewer_role_display = member_roles.get(reviewer.membership.get(semester=review_milestone.assignment.semester).role)
	chunks_enough_same_role_tasks = []
	if simulate:
		# for chunk in chunk_id_task_map.values():
		# 	num_tasks_for_role = get_num_tasks_for_role(review_milestone,reviewer_role)
		# 	if len(chunk['tasks'][reviewer_role_display]) >= num_tasks_for_role:
		# 		logging.info("accepted")
		# 		chunks_enough_same_role_tasks.append(chunk['chunk'].id)
		chunks_enough_same_role_tasks = [i['chunk']['id'] for i in chunk_id_task_map.values() if len(i['tasks'][reviewer_role_display]) >= get_num_tasks_for_role(review_milestone,reviewer_role)]
	else:
		# get all members with the same role in the class
		members_same_role = Member.objects.filter(semester=review_milestone.assignment.semester)
		if reviewer_role == Member.STUDENT or reviewer_role == Member.VOLUNTEER:
			members_same_role = members_same_role.filter(Q(role=Member.STUDENT)|Q(role=Member.VOLUNTEER))
		elif reviewer_role == Member.TEACHER:
			members_same_role = members_same_role.filter(role=Member.TEACHER)
		else:
			members_same_role = Member.objects.none()

		# get all tasks for chunks in this ReviewMilestone with reviewers that have the same role in the class
		tasks_same_role = Task.objects.filter(milestone=review_milestone, reviewer__membership__pk__in=members_same_role)
		# aggregate tasks by the chunk they're for and count the number of tasks for each chunk
		tasks_same_role = tasks_same_role.values('chunk').annotate(Count('id'))

		# remove chunks that need more same role reviewers
		chunks_enough_same_role_tasks = tasks_same_role.filter(id__count__gte=get_num_tasks_for_role(review_milestone,reviewer_role)).values('chunk')

	# get all chunks that already have enough reviewers with the same role in the class
	chunks_enough_same_role_reviewers = chunks.filter(id__in=chunks_enough_same_role_tasks)
	return chunks_enough_same_role_reviewers

# return the maximum allowable number of tasks for a given role for a given chunk
# ex: chunks can only have 1 teacher reviewer
# ex: chunks can only have up to 2 student/volunteer reviewers
def get_num_tasks_for_role(review_milestone,role):
	num_role_per_chunk = 0;
	if role == Member.STUDENT or role == Member.VOLUNTEER:
		num_role_per_chunk = review_milestone.reviewers_per_chunk
		# num_role_per_chunk = 2
	elif role == Member.TEACHER:
		# num_role_per_chunk = review_milestone.teacher_reviewers_per_chunk
		num_role_per_chunk = 1
	return num_role_per_chunk

def get_num_tasks_for_user(review_milestone, user, simulate=False):
	member_role = None
	if simulate:
		member_role = user['membership__role']
	else:
		member_role = Member.objects.get(user=user, semester=review_milestone.assignment.semester).role
	# num_tasks_already_assigned = Task.objects.filter(reviewer=user, milestone=review_milestone).count()
	num_tasks_per_role = 0
	if member_role == Member.STUDENT:
		num_tasks_per_role = review_milestone.student_count
	elif member_role == Member.TEACHER:
		num_tasks_per_role = review_milestone.staff_count
	elif member_role == Member.VOLUNTEER:
		num_tasks_per_role = review_milestone.alum_count
	else:
		num_tasks_per_role = 0
	# return min(0,num_tasks_per_role - num_tasks_already_assigned)
	return num_tasks_per_role

def list_chunks_to_exclude(review_milestone):
	to_exclude = review_milestone.chunks_to_exclude
	if to_exclude == None:
		return []
	return to_exclude.split()



	