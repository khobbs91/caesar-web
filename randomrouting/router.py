from django.conf import settings
import os
# import settings_local

class RandomroutingRouter(object):
    """
    A router to control all database operations on models in the
    randomrouting application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read randomrouting models go to test.
        """
        use_test_db = (os.getenv('USE_TEST_DB') != None)
#        print 'usetestdb', use_test_db
        if use_test_db:
            return 'test'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write randomrouting models go to test.
        """
        use_test_db = (os.getenv('USE_TEST_DB') != None)
        if use_test_db:
            return 'test'
        return None

    # def allow_relation(self, obj1, obj2, **hints):
    #     """
    #     Allow relations if a model in the randomrouting app is involved.
    #     """
    #     return None

    # def allow_migrate(self, db, model):
    #     """
    #     Make sure the randomrouting app only appears in the 'test'
    #     database.
    #     """
    #     if db == 'test':
    #         return model._meta.app_label == 'randomrouting'
    #     elif model._meta.app_label == 'randomrouting':
    #         return False
    #     return None