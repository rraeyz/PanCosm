"""A menu or toolbar action that follows its page button's enabled and hidden state (moved out of area_menus.py)."""

from contextlib import suppress

from PySide6.QtCore import QEvent, QObject


def follow_enabled(button, action):
    """A toolbar or menu action that is enabled exactly when the page's button is, and not while the page has hidden
    the button (Posterior… before an MCMC run); the button stays the one place where the page decides. A button in
    a tab that is not shown is not hidden: its action stays usable."""

    def follow():
        with suppress(RuntimeError):  # the action went with its window while the button lives on
            action.setEnabled(button.isEnabled() and not button.isHidden())

    class _Watch(QObject):
        def eventFilter(self, obj, event):
            if event.type() in (QEvent.EnabledChange, QEvent.ShowToParent, QEvent.HideToParent):
                follow()
            return False

    action._watch = _Watch(button)
    button.installEventFilter(action._watch)
    follow()
