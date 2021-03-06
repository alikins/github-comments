
import unittest

from github_comments.github_comments import parse_args


class TestArgs(unittest.TestCase):
#    def tearDown(self):
#        print self.args

    def _parse_args(self, arg_string):
        self.args = parse_args(arg_string.split())
        #print self.args

    def _assert_defaults(self):
        self.assertTrue(self.args.pr_review_comments)
        self.assertTrue(self.args.pr_comments)
        self.assertFalse(self.args.debug)

    def test_no_args(self):
        self._parse_args("")

    def test_debug(self):
        self._parse_args("-d")
        self.assertTrue(self.args.debug)
        self.assertTrue(self.args.pr_review_comments)
        self.assertFalse(self.args.pr_comments)

    def test_pr_comments(self):
        self._parse_args("-c")
        self.assertTrue(self.args.pr_comments)
        self._assert_defaults()

    def test_comment(self):
        self._parse_args("comment filename lineno fooo")
        self.assertEquals("comment", self.args.subparser_name)
        self.assertEquals("filename", self.args.comment_filename)
        self.assertEquals("lineno", self.args.comment_lineno)
        self.assertEquals('fooo', self.args.comment_body)

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
