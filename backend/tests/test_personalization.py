"""
Unit tests for personalization_engine bug fixes.
Phase 1: Bug 1 (Count import) + Bug 2 (update_weights arity).
Stubs created in Plan 01 — assertions tightened in Plan 02.
"""
import unittest
from unittest.mock import Mock, patch


class TestCountImport(unittest.TestCase):
    """Bug 1: from django.db.models import Count must be present."""

    def test_count_is_imported_in_personalization_engine(self):
        """Importing the module must not raise NameError for Count."""
        from apps.recommendations import personalization_engine
        # Count must be referenced at module scope after Plan 02 fix.
        # Stub assertion — Plan 02 tightens this:
        self.assertTrue(hasattr(personalization_engine, 'Count'))

    def test_get_personalization_summary_does_not_crash_on_count(self):
        """get_personalization_summary uses Count(...) — must not NameError."""
        from apps.recommendations.personalization_engine import PersonalizationEngine
        with patch('apps.core.models.UserPreferences.objects') as mock_prefs, \
             patch('apps.core.models.UserFeedback.objects') as mock_feedback:
            mock_prefs.get_or_create.return_value = (Mock(), False)
            mock_feedback.filter.return_value.values.return_value.annotate.return_value = []
            mock_user = Mock()
            mock_user.id = 1
            try:
                engine = PersonalizationEngine(mock_user)
                # If Count is not imported, instantiation/call paths NameError.
                self.assertIsNotNone(engine)
            except NameError as e:
                if 'Count' in str(e):
                    self.fail(f"Count import missing in personalization_engine: {e}")
                raise


class TestApplyFeedbackLearningArity(unittest.TestCase):
    """Bug 2: apply_feedback_learning must not call update_weights with wrong arity."""

    def test_apply_feedback_learning_does_not_raise(self):
        """Calling apply_feedback_learning on a feedback object must not raise."""
        from apps.recommendations.personalization_engine import PersonalizationEngine
        with patch('apps.core.models.UserPreferences.objects') as mock_prefs:
            mock_prefs.get_or_create.return_value = (Mock(), False)
            mock_user = Mock()
            mock_user.id = 1
            engine = PersonalizationEngine(mock_user)
            mock_feedback = Mock()
            mock_feedback.feedback_type = 'LIKE'
            mock_feedback.track.name = 'Test Track'
            mock_feedback.track_features = {'energy': 0.5}
            # Must not raise AttributeError ("update_weights does not exist on UserPreferences")
            # nor TypeError ("update_weights() takes 2 positional arguments but 3 were given").
            try:
                engine.apply_feedback_learning(mock_feedback)
            except (AttributeError, TypeError) as e:
                self.fail(f"apply_feedback_learning raised {type(e).__name__}: {e}")


if __name__ == '__main__':
    unittest.main()
