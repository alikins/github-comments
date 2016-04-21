github-comments
===============

show pull request comments in a lint like fashion

It also attempts to find any review comments
from pull requests that use the current HEAD.

Usage
====

```
github-comments pr repo_user repo_name pull_request_number
```

or, if you are on a branch that has had pull requested
from it:

```
github-comments
```

Output
=====
The output is of form:

```
some/file.txt:1:billygit_user:pr37: I like this line alot!
some/other/file.ps:123:pr37:some_user: This is a cool like
that continues across
a lot of lines, that
another/file.doc:1:billg:pr37: what?
```

The fields are:
- path to file
- line number of the comment
- which github user made the comment
- the pull request number
- the body of the comment, text'ified and possibly multiline

If the ```--pr-comments``` or `-c` flag will include comments
made on the pull request itself, that will use the
repo_name as the "filename", and an empty line number.

Automatic Mode
=============

If no args are specified, it tries to guess
which pull request to use.

To get automatic mode to work, you need:

- A branch with a merge url set (aka, tracking branch)
- The merge url needs to be a github repo
- The repo needs to have open pull requests against it

Or:

- The branch is a pull request fetched from origin with a name in the
  format 'pr-1234'. 'pr', a '-', and the pr number.

Installation
============
```
python setup.py install
```

Command line options
===================
```
Usage: github-comments [options] [repo_owner] [repo_name] [pull_request_number]

Options:
  -h, --help            show this help message and exit
  -r, --review-comments
  --no-review-comments
  -c, --pr-comments
  -d, --debug
Subcommands:
  auth     ask for and save user auth info
  comment  create a pull request review comment
  pr  [owner] [repo] [pull request number]
            get comments on a particular pull request
  automode  detect pull request to get info for (default)
```

For example,
```
    github-comments pr alikins github-comments 3
```

Will show the review comments for pull request number 3
of the github-comments repo.

Adding the --pr-comments or -c  will also include the non
patch specific comments made on the pull request. ie,
the 'Conversation' comments on the github pull request page.

Using with Vim
==============

github-comments can be used as a "makeprg" file to
generate a list of errors/warnings to investigate.

In vim, set makeprg to github-comments
```
    :set makeprg=github-comments
```

Invoking ':make' or similar will use the output
as an errorlist. ':copen' etc to view files
with comments, etc.

output from 'github-comments' is parseable
as a vim error file as well. So, to
open vim with an error list based on
the comments and jump to the first entry:

```
    vim -q <(github-comments)
```

This executes 'github-comments' and uses
process substitution to create a errorfile
for vim to read.

Another approach:

```
    vim -c ':set makeprg=github-comments' -c ':make'
```

Run vim, setting makeprg and populating quickfixlist
with github-comments.

Authentication
==============

The supported authentication modes are:
- No authentication
- basic auth
- oauth2

Default authentication is no authentication.

Since this is read only, that works fine for public
repos. But it is rate limited.

To create and store a OAUTH token, run with -a/--authentication.
This will prompt for a github username and password, and
create a OAUTH token for that user and this utility and save
it into ~/.github-comments.

To enable http Basic Auth for a user, add a ~/.github-comments
config file. File format is ini file style (ala, ConfigParser),
for example:

```
[main]
username = username
password = password
```

If basic auth is available, github-comments will
request an oauth token for the github-comments
app, with a "public_repo" scope[1], and will
use the OAUTH2 token for the rest of the
connections.

A permanent oauth token can be specified
in the config file with the 'oauth_token'
field (or with the -a/--authenticate option):

```
[main]
oauth_token = 123123123123123123
```


[1] http://developer.github.com/v3/oauth/#scopes

Deps
====

- requests http://python-requests.org/
- markdown https://pypi.python.org/pypi/Markdown

To do
=====

- Improve and hopefully simplify the 'automatic' mode.
- port to use a 3rd party python github module for API
  use instead of the current home rolled and very limited one.
- Find/show commit comments
- Find/show comments on issues reference that pull request?
- a script to do the vim invocation
- add a followable link to the github url somehow
- eventually make api request calls async
