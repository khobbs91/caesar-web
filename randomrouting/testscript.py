from __future__ import division
from django.contrib.auth.models import User
from tasks.models import ChunkReview
from chunks.models import ReviewMilestone, Semester, Chunk
import random
import sys, os
import randomrouting.random_routing as rr
# import logging
# from django.db import transaction
# from django.db import connection

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

    # assign every reviewer in the class
    for r in xrange(l):
        print "assigning reviewer", r, "out of", l
        rr.assign_tasks(review_milestone, reviewers[r])
    
    # ################################################################################################

    print 'look at the db to see changes, then press enter:'
    raw_input()
    print 'rolling back'
    # delete and recreate all ChunkReviews in this ReviewMilestone
    ChunkReview.objects.filter(chunk__file__submission__milestone=review_milestone.submit_milestone).delete()

#    transaction.rollback(using='test')
    
run_test()
print 'rolled back'

print 'cleaning up, press any key to exit'
sys.exit(0)