# classes for git hub authencation for GithubApi class


class GithubAuth(object):
    def __init__(self):
        pass

    def add_to_session(self, requests_session):
        requests_session.auth = None


class GithubNoAuth(GithubAuth):
    auth_type = "no_auth"
    """unauthenticated access"""


class GithubBasicAuth(GithubAuth):
    """http basic auth (user/pass)"""
    auth_type = "basic"

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def info(self):
        return (self.username, self.password)

    def add_to_session(self, requests_session):
        requests_session.auth = self.info()


class GithubOauth2Auth(GithubAuth):
    "Oauth2 based github auth"""
    auth_type = "oauth2"

    def __init__(self, token):
        self.token = token
        # use basic auth to get token

    def add_to_session(self, requests_session):
        requests_session.headers.update({"Authorization": "token %s" % self.token})


def get_auth(cfg):
    # prefer oauth
    if cfg.data.has_option("main", "oauth_token"):
        return GithubOauth2Auth(cfg.data.get("main", "oauth_token"))

    if cfg.data.has_option("main", "username") and cfg.data.has_option("main", "password"):
        user = cfg.data.get("main", "username")
        password = cfg.data.get("main", "password")
        return GithubBasicAuth(user, password)

    # no auth specified
    return GithubNoAuth()
