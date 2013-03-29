
import unittest

from github_comments.github_comments import parse_args


class TestArgs(unittest.TestCase):
#    def tearDown(self):
#        print self.args

    def _parse_args(self, arg_string):
        self.args = parse_args(arg_string.split())

    def _assert_defaults(self):
        self.assertEquals(None, self.args.pr_number)
        self.assertEquals(None, self.args.pr_owner)
        self.assertEquals(None, self.args.pr_repo)

    def test_no_args(self):
        self._parse_args("")

    def test_debug(self):
        self._parse_args("-d")
        self.assertTrue(self.args.debug)
        self._assert_defaults()

    def test_pr_comments(self):
        self._parse_args("-c")
        self.assertTrue(self.args.pr_comments)
        self._assert_defaults()

    def test_owner_repo_pr(self):
        self._parse_args("pr someowner somerepo 37")
        self.assertEquals("someowner", self.args.pr_owner)
        self.assertEquals("somerepo", self.args.pr_repo)
        self.assertEquals("37", self.args.pr_number)

    def test_owner_repo_pr_c_r(self):
        self._parse_args("-c -r pr someowner somerepo 37")
        self.assertEquals("someowner", self.args.pr_owner)
        self.assertEquals("somerepo", self.args.pr_repo)
        self.assertEquals("37", self.args.pr_number)
        #self.assertTrue(self.args.pr_review_comments)
        self.assertTrue(self.args.pr_comments)
