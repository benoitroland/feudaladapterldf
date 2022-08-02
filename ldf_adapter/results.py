# vim: foldmethod=indent : tw=100
# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=logging-fstring-interpolation, logging-not-lazy, logging-format-interpolation
# pylint: disable=missing-docstring, too-few-public-methods
"""Results for feudalClient"""

import sys


class FatalError(Exception):
    """Raised when a fatal error occurs."""

    exit_code: int = 42

    def __init__(self, message: str) -> None:
        print(f"\nERROR: {message}\n")
        sys.exit(FatalError.exit_code)


class Result:
    """A Result returned by the adapter to the feudalClient.

    Serialized to JSON as the final act of this script.
    """

    def __init__(self, state, message):
        """Called by subclasses, usually not directly.

        Arguments:
        state -- The state that was reached. One of 'deployed', 'not_deployed', 'failure' and 'rejected' (see subclasses below).
        message -- Displayed to the user in the feudalClient webinterface.
        """
        self.state = state
        self.message = message

    @property
    def attributes(self):
        return self.__dict__


## Sucessful
class Success(Result):
    """Indicates a successful result (i.e. user was deployed or undeployed)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Deployed(Success):
    """Indicates that the user was successfully deployed to the service."""

    def __init__(self, credentials, **kwargs):
        """Initialises this Result with a state of 'deployed'.

        Arguments:
        credentials -- A dictionary displayed to the user in the feudalClient webinterface.
        **kwargs -- Any additional keyword arguments are passed to Success.__init__
        """
        super().__init__(state="deployed", **kwargs)
        self.credentials = credentials


class NotDeployed(Success):
    """Indicates that the user was successfully undeployed from the service."""

    def __init__(self, **kwargs):
        super().__init__(state="not_deployed", **kwargs)


class Status(Success):
    """Indicates the status of the user."""

    def __init__(self, state, **kwargs):
        super().__init__(state=state, **kwargs)


## Exceptional (Error or Questionnaire)
class ExceptionalResult(Result, Exception):
    """Raise a subclass of this to abort and directly return this Result to the feudalClient"""

    pass


class Failure(ExceptionalResult):
    """Indicates a failure in attempting to deploy/undeploy the user.

    The previous state should be retained, but might also be inconsistent
    """

    def __init__(self, **kwargs):
        super().__init__(state="failed", **kwargs)


class Rejection(ExceptionalResult):
    """Indicates that the user is not allowed to access the requested resource.

    A reason for this might be an insufficient assurance level.
    """

    def __init__(self, **kwargs):
        super().__init__(state="rejected", **kwargs)


class Questionnaire(ExceptionalResult):
    """Additional information is needed to reach the desired state.

    Usually, this is raised during deployment to get additional
    information.  The feudalClient then calls this script again with
    an additional object under the key 'answers' in the
    input dictionary. This can be accessed from within the UserInfo
    class (see below).

    Can be used to ask multiple questions at once.

    Arguments:
    questions -- A Dictionary of `{name: text, ...}` questions. The text is the question
                 displayed to the user in the feudalClient webinterface. The answer
                 submitted by the user can then be found under the key `name` in the
                 answers dictionary.
    defaults -- A Dictionary of `{name: thing, ...}` quenstionaire answers. The `thing` is the
                default value of the named question. The type of thing determines the input of the
                answer. Possible are strings, numbers or lists to provide the user with a selection
                of the given values.
    **kwargs -- Any additional keyword arguments ar passed to ExceptionalResult.__init__
    """

    def __init__(self, questions, defaults, **kwargs):
        super().__init__(state="questionnaire", message="There are unanswered questions.", **kwargs)
        self.questionnaire = questions
        self.questionnaire_answers = defaults


class Question(Questionnaire):
    """Convenience class to ask a single question."""

    def __init__(self, name, text, default=None, **kwargs):
        """See Questionaire.__init__ for details.

        Arguments:
        name -- The name of the question
        text -- Displayed to the user
        default -- The default value / the input type
        **kwargs -- Any additional keyword arguments are passed to Questionaire.__init__
        """
        defaults = {}
        if default:
            defaults[name] = default

        super().__init__(questions={name: text}, defaults=defaults, **kwargs)


def raise_question(*args, **kwargs):
    """Convenice function needed in places where an expression is required.

    E.g: `userinfo.get_value() or raise Question(...)` is not valid,
    but `userinfo.get_value() or raise_question(...)` is.
    """
    raise Question(*args, **kwargs)
