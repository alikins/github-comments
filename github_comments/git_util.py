# miscelanous git utility methods
#
# mostly wrappers around cli invocations

import logging
import subprocess
import sys

log = logging.getLogger(__name__)


# I love regular expressions as much as the next guy, but
# sometimes I just dont want to use them
def find_github_repos():
    """Find remotes that are github, and find the repo name"""
    process = subprocess.Popen(['/usr/bin/git', 'config', '-l'],
                               stdout=subprocess.PIPE)
    git_config = process.communicate()[0]
    config_lines = git_config.splitlines()
    github_repos = set()
    for config_line in config_lines:
        if not config_line.startswith("remote."):
            continue
        key, value = config_line.split('=', 1)
        if not key.endswith('.url'):
            continue

        # verify this is a github repo
        if 'github.com' not in value:
            continue

        parts = key.split('.')
        remote_name = parts[1]

        repo_url = value
        if repo_url.startswith("git@"):
            repo_url_parts = repo_url.rsplit('/', 1)
            name_dot_git = repo_url_parts[-1]
            owner_name = repo_url_parts[-2].split(':', 1)[1]
        elif repo_url.startswith("git://"):
            repo_url_parts = repo_url.split('/')
            name_dot_git = repo_url_parts[-1]
            # can repo's have / in the name?
            owner_name = repo_url_parts[-2]

        # probably sombody with a foo.git/ reponame
        if name_dot_git.endswith('.git'):
            name = name_dot_git[:-4]
        else:
            name = name_dot_git
        github_repos.add((remote_name, owner_name, name))

    log.debug("find_github_repos github_repos=%s", github_repos)
    # TODO: sort this so most likely origin is first
    return github_repos


def get_branch_ref():
    # we could just read and parse .git/HEAD
    # needs to follow through to get upstream branch name
    # see "remote-ref" alias in my gitconfig for example
    process = subprocess.Popen(['/usr/bin/git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                               stdout=subprocess.PIPE)
    this_branch = process.communicate()[0]

    log.debug("get_branch_ref=%s", this_branch)

    return this_branch.strip()


def get_remote_branch_ref(local_ref):
    # see if we have an "upstream" or merge ref
    branch_config_key = "branch.%s.merge" % local_ref
    process = subprocess.Popen(['/usr/bin/git', 'config', '--get', branch_config_key],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    remote_merge_ref_full = process.communicate()[0]
    remote_merge_ref_full.strip()

    if process.returncode > 0:
        sys.stderr.write("No merge ref found for %s\n (no config set for %s) " %
                         (local_ref, branch_config_key))
        return local_ref

    log.debug("remote_merge_ref_full=%s", remote_merge_ref_full)
    # needs to skip remote name here as well
    remote_ref = remote_merge_ref_full[len('refs/heads/'):]

    log.debug("remote_ref=%s", remote_ref)

    return remote_ref.strip()
