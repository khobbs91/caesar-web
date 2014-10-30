"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "./manage.py test".

Replace this with more appropriate tests for your application.
"""

from __future__ import division
from django.test import TestCase
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

# class SimpleTest(TestCase):
#     def test_basic_addition(self):
#         """
#         Tests that 1 + 1 always equals 2.
#         """
#         self.assertEqual(1 + 1, 2)
#         # self.assertEqual(1, 2)

class RoutingTestCase(TestCase):
	fixtures = ['test_fixtures.json']

    def setUp(self):
        # Animal.objects.create(name="lion", sound="roar")
        # Animal.objects.create(name="cat", sound="meow")
        User.objects.create()
        Subject.objects.create()
        Semester.objects.create()
        Assignment.objects.create()
        SubmitMilestone.objects.create()
        ReviewMilestone.objects.create()
        Submission.objects.create()
        File.object.create()
        Chunk.object.create()

    def test_animals_can_speak(self):
        """Animals that can speak are correctly identified"""
        lion = Animal.objects.get(name="lion")
        cat = Animal.objects.get(name="cat")
        self.assertEqual(lion.speak(), 'The lion says "roar"')
        self.assertEqual(cat.speak(), 'The cat says "meow"')



