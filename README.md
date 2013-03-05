github-comments
===============

show pull request comments in a lint like fashion

usage:
./github-comments repouser reponame pull_request_number

output is of form:

some/file.txt:1:billygit_user: I like this line alot!
some/other/file.ps:123:some_user: This is a cool like
that continues across
a lot of lines, that
another/file.doc:1:billg: what?

Needs:

requests http://python-requests.org/
markdown https://pypi.python.org/pypi/Markdown

