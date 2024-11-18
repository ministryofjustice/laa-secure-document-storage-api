# Configure path to casbin model and policy for tests
import os
os.environ['CASBIN_MODEL'] = 'authz/any_authenticated_access.conf'
os.environ['CASBIN_POLICY'] = 'authz/any_authenticated_access.csv'