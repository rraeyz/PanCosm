"""Errors a user can meet, raised with their message template (plans/architecture.md ARC-13, reduced item 3).

    raise AppError("unknown detrending series: {name}", name=name)

An AppError is a ValueError whose text is the filled template, so the interface translates it as before
(ui/messages.py); tests/test_messages.py checks that each template raised this way is one of the message templates
word for word, so a template and its raise cannot drift apart. Existing raises are converted when they are touched.
"""


class AppError(ValueError):
    def __init__(self, template, **values):
        self.template, self.values = template, values
        super().__init__(template.format(**values))
