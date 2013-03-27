#!/usr/bin/python

# show github pull request comments in a lint like format
#
# ala, pep8, jslint, etc, except for code review comments
#
# potentially useful to use with syntastic/flymake/etc
#
# Thoughts:
#   - it would be nice if this was a minimal dep one file script
#   - it would be nice if this could DWIM and find the approriate
#     pull requests automatically
#   - initial use case is "I have a local branch, that I've pushed
#     to github, and isssued a pull request. I would like to see
#     the per line code review comments for that pull request"
#   - may eventually also support showing comments for arbitrary
#     pull requests. for example, if you are reviewing a pull
#     request, you could see the comments other have made
#   - unsure what to do with the primary comments view...
#     - anything that references a file could get it as a per file
#       comment
#     - at least tools like vim makeprg/errorformat/quicklist/make
#       can deal with per project/branch config
#   - it is a little tricky figuring out what the right pull request
#     is, especially if local/remote ref names dont match, and there is
#     no tracking branch. Should be able to find it by tracking donw
#     the right sha's though

from hashlib import md5
# we could ditch the git subprocess probably
import codecs
import ConfigParser
import optparse
import operator
import os
import re
import subprocess
import sys
import types
import pprint

# for parsing html into plain txt
from BeautifulSoup import BeautifulSoup
# for parsing markdown into html, since the comments use it
import markdown
# for http, though curl or even urllib will be okay
# if we stick to a single file util concept
import requests

# from from https://gist.github.com/gasman/856894
# git hub api comment content types stuff doesnt work
# bundle here for lower deps, since it seems that
#
# https://github.com/github/developer.github.com/commit/b6a782f74a4c1a1a28d3ac2bfddbea6f6ae4223c
# seems to imply it was removed
#

# regex for parsing a diff hunk header and finding the offsets and sizes
diff_hunk_pattern = re.compile("^@@ -(\\d+),(\\d+) \\+(\\d+),(\\d+) @@")

DEBUG = False
cfg = None

pp = pprint.pprint

sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)


class GitHubAuth(object):
    def __init__(self):
        pass


class GitHubBasicAuth(GitHubAuth):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def info(self):
        return (self.username, self.password)


# support github api pagination
class GitHubApi(object):
    def __init__(self, host, auth, debug=False):
        self.host = host
        self.debug = debug
        self.auth = auth
        # auth stuff, etc

    def get_url(self, url=None, full_url=None):
        url = full_url or "https://%s/%s" % (self.host, url)
        r = requests.get(url, auth=self.auth.info())
        if self.debug:
            # move to using a logger
            sys.stderr.write("%s:%s\n" % (url, r.status_code))
            sys.stderr.write("%s\n" % pp(r.headers))
        if 'next' in r.links:
            next_data = self.get_url(full_url=r.links['next']['url'])
            data = r.json()
            if self.debug:
                sys.stderr.write("%s\n" % pp(data))
            if isinstance(data, types.DictType):
                return data.update(next_data)
            if isinstance(data, types.ListType):
                return data + next_data
        return r.json()

    def get_pull_request_review_comments(self, pull_request):
        url = "repos/%s/%s/pulls/%s/comments" % \
            (pull_request.repo_owner,
             pull_request.repo_name,
             pull_request.pr_number)
        # I was hoping this would render the markdown to text, but that
        # does not appear to be the case.
        #headers = {'Accept': 'application/vnd.github.v3.text+json',
        #           'User-Agent': 'git-comments via python requests'}

        r_comments = self.get_url(url)
        return r_comments

    def get_pull_request_comments(self, pull_request):
        url = "repos/%s/%s/issues/%s/comments" % \
            (pull_request.repo_owner,
             pull_request.repo_name,
             pull_request.pr_number)
        # I was hoping this would render the markdown to text, but that
        # does not appear to be the case.
        #headers = {'Accept': 'application/vnd.github.v3.text+json',
        #           'User-Agent': 'git-comments via python requests'}

        r_comments = self.get_url(url)
        return r_comments

    def get_compare_commits(self, repo_owner, repo_name, base_sha1, head_sha1):
        url = "repos/%s/%s/compare/%s...%s" % \
            (repo_owner, repo_name, base_sha1, head_sha1)
        results = self.get_url(url)
        return results

    def get_pull_requests(self, repo_owner, repo_name):
        url = "repos/%s/%s/pulls?open" % (repo_owner, repo_name)
        prs = self.get_url(url)

        return prs

    def get_pull_request(self, repo_owner, repo_name, pr_number):
        url = "repos/%s/%s/pulls/%s" % (repo_owner,
                                        repo_name,
                                        pr_number)
        prs = self.get_url(url)
        return prs


class PullRequest(object):
    def __init__(self, repo_owner, repo_name,
                 pr_number, diffs=None, data=None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.diffs = diffs
        self.data = data

    @classmethod
    def create_by_number(cls, github_api, repo_owner, repo_name, pr_number):
        pr = github_api.get_pull_request(repo_owner, repo_name, pr_number)
        return cls(repo_owner, repo_name, pr['number'], data=pr)


class PullRequestList(object):
    def __init__(self, github_api):
        self.github_api = github_api
        self.prs = []

    def find_prs_for_ref(self, repo_owner, repo_name, remote_ref_name):
        """Get all pull request for repo, and filter based on remote_ref_name"""
        prs = self.github_api.get_pull_requests(repo_owner, repo_name)
        # need repo_owner and repo_name to ask for the pull requests
        # TODO: cli arg to check closed pr's as well
        for pr in prs:
            # find the pull request that has match ref name
            if pr['head']['ref'] == u'%s' % remote_ref_name:
                # for the case of a specific pr, we could maybe
                # figure out the file_to_diff locally, but asking
                # the api for it means we dont need to be i a repo
                file_to_diff = self.get_file_to_diff(repo_owner, repo_name,
                                                     pr['base']['sha'],
                                                     pr['head']['sha'])
                self.prs.append(PullRequest(repo_owner, repo_name,
                                            pr['number'],
                                            file_to_diff))

    def add_pr_by_number(self, repo_owner, repo_name, pr_number):
        pr = PullRequest.create_by_number(self.github_api, repo_owner,
                                          repo_name, pr_number)
        file_to_diff = self.get_file_to_diff(repo_owner, repo_name,
                                             pr.data['base']['sha'],
                                             pr.data['head']['sha'])
        pr.diffs = file_to_diff
        self.prs.append(pr)

    def get_file_to_diff(self, repo_owner, repo_name, base_sha, head_sha):
        results = self.github_api.get_compare_commits(repo_owner, repo_name,
                                                      base_sha, head_sha)
        file_to_diff = {}
        for file_data in results['files']:
            if file_data['filename'] in file_to_diff:
                print "ugh, wtf"
            file_to_diff[file_data['filename']] = file_data['patch']

        return file_to_diff


def gfm(text):
    # Extract pre blocks.
    extractions = {}

    def pre_extraction_callback(matchobj):
        digest = md5(matchobj.group(0)).hexdigest()
        extractions[digest] = matchobj.group(0)
        return "{gfm-extraction-%s}" % digest
    pattern = re.compile(r'<pre>.*?</pre>', re.MULTILINE | re.DOTALL)
    text = re.sub(pattern, pre_extraction_callback, text)

    # Prevent foo_bar_baz from ending up with an italic word in the middle.
    def italic_callback(matchobj):
        s = matchobj.group(0)
        if list(s).count('_') >= 2:
            return s.replace('_', '\_')
        return s
    pattern = re.compile(r'^(?! {4}|\t)\w+(?<!_)_\w+_\w[\w_]*', re.MULTILINE | re.UNICODE)
    text = re.sub(pattern, italic_callback, text)

    # In very clear cases, let newlines become <br /> tags.
    def newline_callback(matchobj):
        if len(matchobj.group(1)) == 1:
            return matchobj.group(0).rstrip() + '  \n'
        else:
            return matchobj.group(0)
    pattern = re.compile(r'^[\w\<][^\n]*(\n+)', re.MULTILINE | re.UNICODE)
    text = re.sub(pattern, newline_callback, text)

    # Insert pre block extractions.
    def pre_insert_callback(matchobj):
        return '\n\n' + extractions[matchobj.group(1)]
    text = re.sub(r'{gfm-extraction-([0-9a-f]{32})\}', pre_insert_callback, text)

    return text


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
        github_repos.add((owner_name, name))
    return github_repos


def get_branch_ref():
    # we could just read and parse .git/HEAD
    # needs to follow through to get upstream branch name
    # see "remote-ref" alias in my gitconfig for example
    process = subprocess.Popen(['/usr/bin/git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                               stdout=subprocess.PIPE)
    this_branch = process.communicate()[0]
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
    # needs to skip remote name here as well
    remote_ref = remote_merge_ref_full[len('refs/heads/'):]
    return remote_ref.strip()


# given comment object, figure out which lines of the
# new file the comment corresponds to. Involves a little
# of parsing a diff (reading the hunk header, and keeping
# track of insertions and deletions)
def find_comment_line(comment, pull_request):
    """returns line of latest version of file that comment applies to.

    Returns an int linenumber if the comment applies, None
    otherwise
    """
    #op = int(comment['original_position'])
    if comment['position']:
        p = int(comment['position'])
    else:
        # outdated diff
        return None

    diff_hunk = pull_request.diffs[comment['path']]
    diff_hunk_lines = diff_hunk.splitlines()
    # The position index is against the full diff, not just the hunk
    # but we want to compute final line. new approach...
    # - go to 'position' offset, then count backwards till we hit
    # a chunk header, then parse the header line to find this chunks
    # "new_start" line. Then comment_line = new_start +
    # distance_from_p_to_header

    count = 0
    for line in reversed(diff_hunk_lines[:p]):
        # we found a header line
        if line[:2] == "@@":
            matches = diff_hunk_pattern.match(line)
            if matches:
                groups = matches.groups()
                new_start = groups[2]
                break
            else:
                continue
        # dont count '-' lines
        if line[0] in ['+', ' ']:
            count += 1
    comment_line = int(new_start) + count
    return comment_line


def format_comment_body(comment):
    body_text_gfm = comment['body']
    body_text_md = gfm(body_text_gfm)
    body_text_html = markdown.markdown(body_text_md)
    body_text_lines = (BeautifulSoup(body_text_html).findAll(text=True))

    body_text = u"\n".join(body_text_lines)
    return body_text


def show_pull_request_review_comments(comments, pull_request):
    # unified diff chunk header
    # lets sort the comments by path
    # we probably want to eventually subsort on computed line offset,
    # and to put the comments in order they were added
    #  so we probably need to figure out the comments and store
    # the order based on the computed stuff, then walk over them
    # again and display
    # sort by file path

    comments.sort(key=operator.itemgetter('path'))
    for comment in comments:
        comment_line = find_comment_line(comment, pull_request)
        if comment_line is None:
            # no comment applies
            continue

        body_text = format_comment_body(comment)
        # this is less broken now
        print u"%s:%s:%s:pr%s: %s" % (comment['path'], comment_line,
                                     comment['user']['login'],
                                     pull_request.pr_number,
                                     body_text)


def show_pull_request_comments(comments, pull_request):
    for comment in comments:
        body_text = format_comment_body(comment)
        print u"%s:%s:pr%s: %s" % (pull_request.repo_name,
                                  comment['user']['login'],
                                  pull_request.pr_number,
                                  body_text)


#FIXME, turn on basic auth just to not get rate limited so
# much for testing. Need to add oauth support
# also,
def read_user_cfg():
    global cfg

    cfg_file = os.path.expanduser("~/.github-comments")
    if not os.access(cfg_file, os.R_OK):
        return None
    cfg = ConfigParser.ConfigParser()
    cfg.read(cfg_file)
    return cfg


def get_auth():
    global cfg
    if cfg is None:
        print "no user cfg, using basic auth"
        return None
    user = cfg.get("main", "username")
    password = cfg.get("main", "password")
    return user, password


def main():
    repo_name = None
    repo_owner = None

    parser = optparse.OptionParser()
    parser.add_option("-r", "--review-comments", dest="pr_review_comments",
                      action="store_true", default=True)
    parser.add_option("--no-review-comments", dest="pr_review_comments",
                      action="store_false")
    parser.add_option("-c", "--pr-comments", dest="pr_comments",
                      action="store_true", default=False)
    parser.add_option("-d", "--debug", dest="debug",
                      action="store_true", default=False)
    options, args = parser.parse_args()

    read_user_cfg()

    # hook up oauth, etc
    username, password = get_auth()
    github_auth = GitHubBasicAuth(username, password)

    github_api = GitHubApi("api.github.com", github_auth,
                           debug=options.debug)
    pull_requests = PullRequestList(github_api)

    # clearly not the most rebust arg handling yet
    if len(args) > 1:
        try:
            repo_owner = args[0]
            repo_name = args[1]
            pull_request_number = args[2]
            pull_requests.add_pr_by_number(repo_owner,
                                           repo_name,
                                           pull_request_number)
        except Exception:
            print "usage: github-comments repo_name pr_number"
    else:
        # well then, let's guess!

        # local branch name
        local_ref_name = get_branch_ref()

        # look up the merge ref, if we dont have one, skip it.
        # we could probably take some guesss...
        remote_ref_name = get_remote_branch_ref(local_ref_name)

        # lets find all the github repo's this could be a branch of,
        # ignoring multiple remote names for the same repo
        github_repos = find_github_repos()

        for github_repo in github_repos:
            repo_owner, repo_name = github_repo

            # does it make sense to support multiple per requests per
            # branch? Suppose you can push a branch to a fork, and then
            # make multiple pull requests to different upstreams?
            pull_requests.find_prs_for_ref(repo_owner, repo_name,
                                           remote_ref_name)

    # see list of pull commits, including info about the ref of the branch
    # it was created for.
    # https://api.github.com/repos/candlepin/subscription-manager/pulls?open

    # set errorformat='%f:%l:%m,%E%f:%l:%m,%-Z%^%$

    if not pull_requests.prs:
        sys.stderr.write("no open pull requests found\n")
        sys.exit()

    for pull_request in pull_requests.prs:
        if options.pr_comments:
            pr_comments = github_api.get_pull_request_comments(pull_request)
            show_pull_request_comments(pr_comments, pull_request)
        if options.pr_review_comments:
            pr_review_comments = github_api.get_pull_request_review_comments(pull_request)
            show_pull_request_review_comments(pr_review_comments, pull_request)
