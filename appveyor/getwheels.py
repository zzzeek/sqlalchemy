# coding: utf-8
from __future__ import absolute_import, division, print_function

import os
import sys
from textwrap import dedent

import requests

URL = 'https://ci.appveyor.com/api'
TOKEN = os.getenv('APPVEYOR_TOKEN')
ACCOUNT = 'zzzeek'  # AppVeyor username, assuming zzzeek
PROJECT = 'sqlalchemy'

if len(sys.argv) != 2:
    sys.exit('getwheels.py <branch>')

if TOKEN is None:
    sys.exit('APPVEYOR_TOKEN env var not set.')

branch = sys.argv[1]

session = requests.Session()
session.headers.update({'Authorization': 'Bearer ' + TOKEN})

BRANCH_BUILD_URL = '{}/projects/{}/{}/branch/{}'.format(
    URL, ACCOUNT, PROJECT, branch)

response = session.get(BRANCH_BUILD_URL)
response.raise_for_status()

build_data = response.json()['build']

message = dedent('''
    Downloading wheels for latest build on branch {bd[branch]!r}.

    Branch:          {bd[branch]}
    AppVeyor build:  {bd[buildNumber]}
    Commit ID:       {bd[commitId]}
    Commit message:  {bd[message]}

    Build status:    {bd[status]}
'''.format(bd=build_data))

print(message)

if build_data['status'] == 'failed':
    sys.exit('Build failed, aborting download.')
elif build_data['status'] == 'running':
    sys.exit('Build still running, aborting download.')

job_ids = [job['jobId'] for job in build_data['jobs']]


def download_artifact(artifact):
    FILE_URL = '{}/buildjobs/{}/artifacts'.format(
        URL, job_id, artifact['fileName'])

    print('Downloading', artifact['fileName'])

    response = session.get(FILE_URL, stream=True)
    response.raise_for_status()

    with open(artifact['fileName'], 'wb') as fp:
        for chunk in response.iter_content(chunk_size=100 * 1024):
            fp.write(chunk)

try:
    os.mkdir('dist')
except OSError:
    pass

for job_id in job_ids:
    ARTIFACTS_URL = '{}/buildjobs/{}/artifacts'.format(URL, job_id)
    response = session.get(ARTIFACTS_URL)
    for artifact in response.json():
        if artifact['fileName'].endswith('.whl'):
            download_artifact(artifact)
