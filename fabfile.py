from __future__ import with_statement
from fabric.api import *

import uuid

env.roledefs = {
    'staging': ['django-staging.torchbox.com'],
    'production': ['tbxwagtail@by-web-2.torchbox.com'],
}

# TODO:
# DATABASES = {
#     'staging':{
#         'name': 'tbxwagtail',
#         'user': 'tbxwagtail',
#     }
#     'production':{
#         'host': 'by-postgres-a.torchbox.com',
#         'name': 'wagtail-torchbox',
#         'user': 'tbxwagtail',
#     }
# }

STAGING_DB_USERNAME = "tbxwagtail"
STAGING_DB_NAME = "tbxwagtail"
LIVE_DB_USERNAME = "tbxwagtail"
LIVE_DB_SERVER = "by-postgres-a.torchbox.com"
DB_NAME = "wagtail-torchbox"
LOCAL_DUMP_PATH = "/home/vagrant/"
REMOTE_DUMP_PATH = "~/"


@roles('staging')
def deploy_staging():
    with cd('/usr/local/django/tbxwagtail/'):
        with settings(sudo_user='tbxwagtail'):
            sudo("git pull")
            sudo("git submodule update")
            sudo("/usr/local/django/virtualenvs/tbxwagtail/bin/pip install -r requirements/production.txt")
            sudo("/usr/local/django/virtualenvs/tbxwagtail/bin/python manage.py syncdb --settings=tbx.settings.production --noinput")
            sudo("/usr/local/django/virtualenvs/tbxwagtail/bin/python manage.py migrate --settings=tbx.settings.production --noinput")
            sudo("/usr/local/django/virtualenvs/tbxwagtail/bin/python manage.py collectstatic --settings=tbx.settings.production --noinput")
            sudo("/usr/local/django/virtualenvs/tbxwagtail/bin/python manage.py compress --force --settings=tbx.settings.production")

        sudo("supervisorctl restart tbxwagtail")

@roles('production')
def deploy():
    with cd('/usr/local/django/tbxwagtail/'):
        run("git pull")
        run("git submodule update")

        run("/usr/local/django/virtualenvs/tbxwagtail/bin/pip install -r requirements/production.txt")
        run("/usr/local/django/virtualenvs/tbxwagtail/bin/python manage.py syncdb --settings=tbx.settings.production --noinput")
        run("/usr/local/django/virtualenvs/tbxwagtail/bin/python manage.py migrate --settings=tbx.settings.production --noinput")
        run("/usr/local/django/virtualenvs/tbxwagtail/bin/python manage.py collectstatic --settings=tbx.settings.production --noinput")
        run("/usr/local/django/virtualenvs/tbxwagtail/bin/python manage.py compress --settings=tbx.settings.production")

    run("sudo supervisorctl restart tbxwagtail")
    #sudo("/usr/local/django/virtualenvs/tbxwagtail/bin/python manage.py update_index --settings=tbx.settings.production")

@roles('production')
def pull_live_data():
    filename = "%s-%s.sql" % (DB_NAME, uuid.uuid4())
    local_path = "%s%s" % (LOCAL_DUMP_PATH, filename)
    remote_path = "%s%s" % (REMOTE_DUMP_PATH, filename)
    local_db_backup_path = "%svagrant-%s-%s.sql" % (LOCAL_DUMP_PATH, DB_NAME, uuid.uuid4())

    run('pg_dump -U%s -h %s -cf %s' % (LIVE_DB_USERNAME, LIVE_DB_SERVER, remote_path))
    run('gzip %s' % remote_path)
    get("%s.gz" % remote_path, "%s.gz" % local_path)
    run('rm %s.gz' % remote_path)
    
    local('pg_dump -Upostgres -cf %s %s' % (local_db_backup_path, DB_NAME))
    puts('Previous local database backed up to %s' % local_db_backup_path)
    
    local('dropdb -Upostgres %s' % DB_NAME)
    local('createdb -Upostgres %s' % DB_NAME)
    local('gunzip %s.gz' % local_path)
    local('psql -Upostgres %s -f %s' % (DB_NAME, local_path))
    local ('rm %s' % local_path)

@roles('staging')
def push_staging_media():
    media_filename = "%s-%s-media.tar" % ('wagtail-torchbox', uuid.uuid4())
    local_media_dump = "%s%s" % (LOCAL_DUMP_PATH, media_filename)
    remote_media_dump = "%s%s" % (REMOTE_DUMP_PATH, media_filename)

    # tar and upload media
    local('tar -cvf %s media' % local_media_dump)
    local('gzip %s' % local_media_dump)
    put(local_media_dump, remote_media_dump)

    # unzip everything
    with cd('/usr/local/django/tbxwagtail/'):
        sudo('rm -rf media')
        sudo('mv %s .' % remote_media_dump)
        sudo('tar -xzvf %s' % remote_media_dump)

@roles('staging')
def push_staging_data():
    db_filename = "%s-%s.sql" % (DB_NAME, uuid.uuid4())
    local_path = "%s%s" % (LOCAL_DUMP_PATH, db_filename)
    remote_path = "%s%s" % (REMOTE_DUMP_PATH, db_filename)
    live_db_backup_path = "%s%s-%s.sql" % (REMOTE_DUMP_PATH, DB_NAME, uuid.uuid4())

    # dump and upload db
    local('pg_dump -Upostgres -c %s > %s' % (DB_NAME, local_path))
    local('gzip %s' % local_path)
    put("%s.gz" % local_path, "%s.gz" % remote_path)

    run('pg_dump -U%s -c %s > %s' % (STAGING_DB_USERNAME, STAGING_DB_NAME, live_db_backup_path))
    puts('Previous live database backed up to %s' % live_db_backup_path)
    
    run('gunzip %s.gz' % remote_path)
    run('psql -U%s -f %s %s' % (STAGING_DB_USERNAME, remote_path, STAGING_DB_NAME))
    run('rm %s' % remote_path)

