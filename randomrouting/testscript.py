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
import sys, os
import logging
import randomrouting.random_routing as rr
import settings_local
from django.db import transaction
from django.db import connection

use_test_db = (os.getenv('USE_TEST_DB') != None)
assert(use_test_db)

# .using('test') will force a single command to use the test database
# print "assignment count:", Assignment.objects.using('test').count()

# FYI: this logging does not show transaction queries
import logging
l = logging.getLogger('django.db.backends')
l.setLevel(logging.DEBUG)
l.addHandler(logging.StreamHandler())

#@transaction.commit_manually(using='test')
def run_test():
#    transaction.commit(using='test')

    ################################################################################################

    # print "assignment count:", Assignment.objects.count()
    # a = Assignment.objects.all()[2]
    # print "old name:", a.name
    # a.name = "hiiii"
    # print "new name:", a.name
    # a.save()

    # run assign_tasks()
    # run unit tests()
    
    print
    print
    semester = Semester.objects.all()[0]
    print "testing assign_tasks for every member of semester:", semester
    print
    print "which review milestone would you like to perform a routing for?"
    # print "choose from one of the following:", [int(rm.id) for rm in list(ReviewMilestone.objects.all())]
    print "choose an id from one of the following:"
    for rm in list(ReviewMilestone.objects.all()):
        print str(int(rm.id))+":",rm.assignment.name
    review_milestone = ReviewMilestone.objects.get(id=int(raw_input()))
    print "review milestone selected:", review_milestone
    reviewers = list(User.objects.filter(membership__semester=review_milestone.assignment.semester))
    random.shuffle(reviewers)
    print "assigning reviewers... this may take a while--please be patient."
    l = len(reviewers)
    #l = 30
    for r in xrange(l):
        print "assigning reviewer", r, "out of", l
        rr.assign_tasks(review_milestone, reviewers[r])
    
    ################################################################################################

    print 'look at the db to see changes, then press any key:'
    raw_input()
    print 'rolling back'

    #delete all tasks in the db
    l = Task.objects.count()
    tasks = list(Task.objects.all())
    #print l, "tasks to delete"
    for t in xrange(l):
        #print "deleting task", t, "out of", l
        tasks[t].delete()

#    transaction.rollback(using='test')
    
run_test()
# b = Assignment.objects.all()[2]
# print 'rolled back i is now', b.name
print 'rolled back'

print 'cleaning up, press any key to exit'
sys.exit(0)