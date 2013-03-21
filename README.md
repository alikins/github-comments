github-comments
===============

show pull request comments in a lint like fashion

It also attempts to find any review comments
from pull requests that use the current HEAD.

Usage
====

```
github-comments repo_user repo_name pull_request_number
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

If the ```--pr-comments``` flag will include comments
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


Installation
============
Make sure the deps mentioned in Deps are installed,
and copy github-comments into your path.


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
```

For example,
```
    github-comments alikins github-comments 3
```

Will show the review comments for pull request number 3
of the github-comments repo.

Adding the --pr-comments will also include the non
patch specific comments made on the pull request.

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

Authentication
==============

Currently, only unauthenticated access (the default), and
basic authentication is supported.

To enable http Basic Auth for a user, add a ~/.github-comments
config file. File format is ini file style (ala, ConfigParser),
for example:

```
[main]
username = username
password = password
```

Deps
====

- requests http://python-requests.org/
- markdown https://pypi.python.org/pypi/Markdown


