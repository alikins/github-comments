github-comments
===============

show pull request comments in a lint like fashion

It also attempts to find any review comments
from pull requests that use the current HEAD.

Usage
====

```
github-comments repouser reponame pull_request_number
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

Deps
====

- requests http://python-requests.org/
- markdown https://pypi.python.org/pypi/Markdown

Automatic Mode
=============

If no args are specified, it tries to guess
which pull request to use. 

To get automatic mode to work, you need:

- A branch with a merge url set (aka, tracking branch)
- The merge url needs to be a github repo
- The repo needs to have open pull requests against it


