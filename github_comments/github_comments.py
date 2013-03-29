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

import argparse
import codecs
import ConfigParser
import getpass
import json
import logging
import operator
import os
import pprint
import re
import sys
import types

# for parsing html into plain txt
from BeautifulSoup import BeautifulSoup
# for parsing markdown into html, since the comments use it
import markdown
# for http, though curl or even urllib will be okay
# if we stick to a single file util concept
import requests

import gfm
import github_auth
import git_util

log = logging.getLogger("github-comments")
logging.basicConfig()

# git hub api comment content types stuff doesnt work
# bundle here for lower deps, since it seems that
#
# https://github.com/github/developer.github.com/commit/b6a782f74a4c1a1a28d3ac2bfddbea6f6ae4223c
# seems to imply it was removed
#

# regex for parsing a diff hunk header and finding the offsets and sizes
diff_hunk_pattern = re.compile("^@@ -(\\d+),(\\d+) \\+(\\d+),(\\d+) @@")

DEBUG = False

pp = pprint.pprint

# let sys.stdout/err handle UTF-8 since it
# will default to 'ascii' for pipes
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)


# support github api pagination
class GithubApi(object):
    def __init__(self, host, auth, debug=False):
        self.host = host
        self.debug = debug
        self.auth = auth
        # auth stuff, etc
        self.session = requests.Session()

        self.add_auth_to_session()

        self.update_auth()

    def add_auth_to_session(self):
        # attach auth info
        # new session with new auth
        self.session = requests.Session()
        self.auth.add_to_session(self.session)

    def update_auth(self):
        # if we started with basic auth, update to
        # oauth for this session
        if self.auth.auth_type in ["oauth2", "no_auth"]:
            return

        data = {'scopes': ['public_repo'],
                'note': 'github-comments'}

        oauth_info = self.post_authorizations(data=data)
        oauth_token = oauth_info['token']

        self.auth = github_auth.GithubOauth2Auth(oauth_token)
        self.add_auth_to_session()

    def post_url(self, url=None, full_url=None, data=None):
        url = full_url or "https://%s/%s" % (self.host, url)
        r = self.session.post(url, data=json.dumps(data))
        return r.json()

    def post_authorizations(self, data=None):
        url = "authorizations"
        r_authorizations = self.post_url(url=url, data=data)
        return r_authorizations

    def get_url(self, url=None, full_url=None):

        url = full_url or "https://%s/%s" % (self.host, url)
        r = self.session.get(url)
        if self.debug:
            # move to using a logger
            sys.stderr.write("auth: %s\n" % self.auth)
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
        print "pr", pr
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
    body_text_md = gfm.gfm(body_text_gfm)
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


class GitHubCommentsConfig(object):
    def __init__(self, filename=None):
        self.filename = filename or os.path.expanduser("~/.github-comments")
        self.data = ConfigParser.SafeConfigParser()

    def read(self):
        # no config file to read
        if os.access(self.filename, os.R_OK):
            self.data.read([self.filename])
        else:
            # empty config
            self.data.add_section("main")

    def save(self):
        self.data.write(open(self.filename, 'w'))


def post_comment_args(args):
    print "post_comments_args", args


def pull_request_args(args):
    print "pull_request_args", args


# cli password reader for auth setup
def get_username():
    username = None
    username = raw_input("username: ")
    return username


def get_password():
    password = None
    password = getpass.getpass("password: ")
    return password


def parse_args(args_list=None):
    # set a default command before

    global_parser = argparse.ArgumentParser(add_help=False)

    global_parser.add_argument("-r", "--review-comments", dest="pr_review_comments",
                               action="store_true", default=True)
    global_parser.add_argument("--no-review-comments", dest="pr_review_comments",
                               action="store_false")
    global_parser.add_argument("-c", "--pr-comments", dest="pr_comments",
                               action="store_true")
    global_parser.add_argument("-d", "--debug", dest="debug",
                               action="store_true")

    global_args, unknown_args = global_parser.parse_known_args(args_list)

    if len(unknown_args) == 0:
        unknown_args.insert(1, "automode")

    parser = argparse.ArgumentParser(parents=[global_parser])
    subparsers = parser.add_subparsers(help='sub commands', dest="subparser_name")

    # github-comments comment somefile 37 "this is the rest of the comment"
    post_comment_parser = subparsers.add_parser('comment')
    post_comment_parser.add_argument("comment_filename", action="store", nargs="?", default=None)
    post_comment_parser.add_argument("comment_lineno", action="store", nargs="?", default=None)
    post_comment_parser.add_argument("comment_body", action="store", nargs="?", default=None)
    #    post_comment_parser.set_defaults(func=post_comment_args)

    pr_parser = subparsers.add_parser('pr')
    pr_parser.add_argument("pr_owner", action="store", nargs='?', default=None)
    pr_parser.add_argument("pr_repo", action="store", nargs='?', default=None)
    pr_parser.add_argument("pr_number", action="store", nargs='?', default=None)

    auth_parser = subparsers.add_parser('auth')
    auth_parser.add_argument("--username", dest="auth_username",
                             action="store", nargs="?", default=None)
    auth_parser.add_argument("--password", dest="auth_password",
                             action="store", nargs="?", default=None)

    subparsers.add_parser('automode', add_help=False)

    # ugh, no default subcommand
    args = parser.parse_args(unknown_args)
    if args.debug:
        log.setLevel(logging.DEBUG)
        log.debug("args: %s\n" % args)

    return args


def main():
    repo_name = None
    repo_owner = None

    cfg = GitHubCommentsConfig()
    cfg.read()

    args = parse_args(sys.argv[1:])

    if args.subparser_name == 'auth':
        # connect basic, get oauth token, save it in cfg,
        # and reload config
        if args.auth_username:
            username = args.auth_username
        else:
            username = get_username()

        if args.auth_password:
            password = args.auth_password
        else:
            password = get_password()

        github_api = GithubApi("api.github.com",
                               github_auth.GithubBasicAuth(username, password))
        github_api.update_auth()
        oauth_token = github_api.auth.token
        cfg.data.set("main", "oauth_token", oauth_token)
        cfg.save()
        cfg = GitHubCommentsConfig()
        cfg.read()

    gh_auth = github_auth.get_auth(cfg)

    github_api = GithubApi("api.github.com", gh_auth,
                           debug=args.debug)

    pull_requests = PullRequestList(github_api)
    # clearly not the most rebust arg handling yet
    if args.subparser_name == 'pr':
        try:
            repo_owner = args.pr_owner
            repo_name = args.pr_repo
            pull_request_number = args.pr_number
            pull_requests.add_pr_by_number(repo_owner,
                                           repo_name,
                                           pull_request_number)
        except Exception:
            print "usage: github-comments repo_owner repo_name pr_number"
            raise

    if args.subparser_name == 'automode':
        # well then, let's guess!

        # local branch name
        local_ref_name = git_util.get_branch_ref()

        # look up the merge ref, if we dont have one, skip it.
        # we could probably take some guesss...
        remote_ref_name = git_util.get_remote_branch_ref(local_ref_name)

        # lets find all the github repo's this could be a branch of,
        # ignoring multiple remote names for the same repo
        github_repos = git_util.find_github_repos()

        for github_repo in github_repos:
            repo_owner, repo_name = github_repo

            # does it make sense to support multiple per requests per
            # branch? Suppose you can push a branch to a fork, and then
            # make multiple pull requests to different upstreams?
            pull_requests.find_prs_for_ref(repo_owner, repo_name,
                                           remote_ref_name)

    if args.subparser_name == 'comment':
        print "look, I'm adding a comment! %s %s %s" % (args.comment_filename,
                                                        args.comment_lineno,
                                                        args.comment_body)
        sys.exit()
    # see list of pull commits, including info about the ref of the branch
    # it was created for.
    # https://api.github.com/repos/candlepin/subscription-manager/pulls?open

    # set errorformat='%f:%l:%m,%E%f:%l:%m,%-Z%^%$

    if not pull_requests.prs:
        sys.stderr.write("no open pull requests found\n")
        sys.exit()

    for pull_request in pull_requests.prs:
        if args.pr_comments:
            pr_comments = github_api.get_pull_request_comments(pull_request)
            show_pull_request_comments(pr_comments, pull_request)
        if args.pr_review_comments:
            pr_review_comments = github_api.get_pull_request_review_comments(pull_request)
            show_pull_request_review_comments(pr_review_comments, pull_request)

if __name__ == "__main__":
    main()
