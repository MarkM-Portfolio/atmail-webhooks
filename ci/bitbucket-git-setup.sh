#!/bin/sh
# v1.0.0
# bitbucket git setup
# This is meant to run *inside* docker containers that need
# to retrieve private git repos from bitbucket
set -ue

mkdir -p ~/.ssh/

if [ -f .ssh/id_rsa ];then
    # Bitbucket pipeline docker implementation make the files mounted from -v
    # owned by nobody:nogroup and that ownership cannot be changed even by
    # copying the file, so creating a new file with the content instead
    cat .ssh/id_rsa > ~/.ssh/id_rsa
    chown root:root ~/.ssh/id_rsa
    chmod 0600 ~/.ssh/id_rsa
fi

# Fingerprint for the Bitbucket site are only added to the build agent,
# not the docker containers called from it. So we need to add them here
ssh-keyscan bitbucket.org > ~/.ssh/known_hosts 2>/dev/null

# Make sure we do not get stuck if for any reason the fingerprint does not match
printf '\nHost bitbucket.org\n  StrictHostKeyChecking=yes\n' >> ~/.ssh/config
chmod 0400 ~/.ssh/config

# Override default URLs to use the ssh access as we are using public/private
# keys for auth
git config --global url."git@bitbucket.org:".insteadOf "https://bitbucket.org/"

# This assumes we are mounting to /src. 
# Fixes: fatal: detected dubious ownership in repository at '<path to the repository>'
# See: https://github.com/git/git/commit/8959555cee7ec045958f9b6dd62e541affb7e7d9
#      https://nvd.nist.gov/vuln/detail/cve-2022-24765
git config --global --add safe.directory /src

exit 0

