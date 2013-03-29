#!/usr/bin/python

from setuptools import setup, find_packages

setup(name="github-comments",
      version='1.3',
      url="https://github.com/alikins/github-comments",
      description="show pull request comments in a lint like fashion",
      author="Adrian Likins",
      author_email="adrian@likins.com",
      packages=find_packages(),
      install_requires=['argparse', 'requests', 'PyGithub'],
      #scripts=["scripts/github-comments"],)
      entry_points={'console_scripts': ['github-comments = github_comments.github_comments:main']})
