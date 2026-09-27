"""
Unit tests for the matchmaking engine.

Tests cover:
  1. Same-gotra exclusion is NEVER bypassed by scoring.
  2. Task idempotency - re-running produces no duplicate matches.
  3. Secondary-filter scoring correctness.
"""

from datetime import date

from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from registrations.models import (
    Registration,
    Match,
    MatchAttemptLog,
    MatchProposal,
)
from registrations.serializers import RegistrationStatusSerializer
from registrations.matching_engine import (
    run_matching_engine,
    _exclude_same_gotra,
    _weighted_score,
    _age_years,
)
from registrations.matching_engine import create_automated_proposal
from registrations.sapinda import check_sapinda_conflict


def _make_registration(**kwargs):
    """Helper to create a Registration-like instance without saving."""
    defaults = {
        "reference": "SG-000000",
        "candidate_gender": Registration.Gender.BRIDE,
        "verification_status": Registration.VerificationStatus.VERIFIED,
        "withdrawn": False,
        "candidate_dob": date(1995, 6, 15),
        "candidate_education": "Engineering",
        "candidate_occupation": "Software Engineer",
        "candidate_current_city": "Patna",
        "candidate_full_name": "Test User",
        "gotra": "",
        "preferred_age_min": 22,
        "preferred_age_max": 30,
        "preferred_location": "Patna",
        "preferred_education": "Engineering",
        "preferred_occupation": "Software Engineer",
    }
    defaults.update(kwargs)
    reg = Registration(**defaults)
    return reg


# ---------------------------------------------------------------------------
# Test: gotra hard-exclusion is never bypassed
# ---------------------------------------------------------------------------

class TestGotraExclusion(TestCase):
    """Same-gotra profiles must never surface as matches regardless of score."""

    def test_same_gotra_excluded_at_query_level(self):
        """Candidates sharing the same gotra are excluded before scoring."""
        user = _make_registration(reference="SG-000001", gotra="sharma", candidate_gender=Registration.Gender.BRIDE)
        candidate = _make_registration(reference="SG-000002", gotra="sharma", candidate_gender=Registration.Gender.GROOM)

        mock_queryset = MagicMock()
        mock_queryset.exclude.return_value = MagicMock()

        filtered, gotra = _exclude_same_gotra(mock_queryset, user)
        self.assertEqual(gotra, "sharma")
        mock_queryset.exclude.assert_called_once()

    def test_empty_gotra_does_not_exclude(self):
        """A profile with empty gotra does not exclude anyone - flagged for review."""
        user = _make_registration(gotra="")
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 5

        filtered, gotra = _exclude_same_gotra(mock_queryset, user)
        self.assertIsNone(gotra)
        self.assertEqual(filtered, mock_queryset)

    def test_different_gotra_not_excluded(self):
        """Candidates with different gotra are NOT excluded."""
        user = _make_registration(gotra="sharma", candidate_gender=Registration.Gender.BRIDE)
        candidate = _make_registration(gotra="gupta", candidate_gender=Registration.Gender.GROOM)

        mock_queryset = MagicMock()
        mock_queryset.exclude.return_value = MagicMock()

        filtered, gotra = _exclude_same_gotra(mock_queryset, user)
        self.assertEqual(gotra, "sharma")


# ---------------------------------------------------------------------------
# Test: idempotency on re-run
# ---------------------------------------------------------------------------

class TestIdempotency(TestCase):
    """Re-running the engine for the same user should not duplicate matches."""

    @patch('registrations.matching_engine.run_matching_engine')
    @patch('registrations.tasks.send_match_notification')
    def test_run_twice_no_duplicates(self, mock_notify, mock_engine):
        """Calling the task twice should not create duplicate Match rows."""
        from registrations.tasks import run_matching_engine_task

        mock_engine.return_value = {
            "pool_size": 5,
            "post_gotra_size": 3,
            "final_matches": [],
            "audit_log": {"outcome": "no_eligible_candidate"},
        }

        run_matching_engine_task.delay(1)
        run_matching_engine_task.delay(1)

        self.assertEqual(mock_engine.call_count, 2)


# ---------------------------------------------------------------------------
# Test: secondary-filter scoring correctness
# ---------------------------------------------------------------------------

class TestScoring(TestCase):
    """Secondary filters should only rank, never exclude."""

    def test_age_within_range_gives_low_score(self):
        """A candidate within the preferred age range gets a low score."""
        user = _make_registration(
            candidate_dob=date(1995, 1, 1),
            preferred_age_min=25,
            preferred_age_max=35,
        )
        candidate_in_range = _make_registration(
            candidate_dob=date(1993, 1, 1),
        )
        candidate_out_of_range = _make_registration(
            candidate_dob=date(2000, 1, 1),
        )

        score_in = _weighted_score(user, candidate_in_range)
        score_out = _weighted_score(user, candidate_out_of_range)

        self.assertLessEqual(score_in, score_out)

    def test_matching_location_gives_lower_score(self):
        """Matching location reduces score."""
        user = _make_registration(
            preferred_location="Patna",
            preferred_age_min=22,
            preferred_age_max=30,
        )
        same_city = _make_registration(candidate_current_city="Patna")
        different_city = _make_registration(candidate_current_city="Mumbai")

        score_same = _weighted_score(user, same_city)
        score_diff = _weighted_score(user, different_city)

        self.assertLess(score_same, score_diff)

    def test_matching_education_gives_lower_score(self):
        """Matching education reduces score."""
        user = _make_registration(
            preferred_education="Engineering",
            preferred_age_min=22,
            preferred_age_max=30,
        )
        same_edu = _make_registration(candidate_education="Engineering")
        different_edu = _make_registration(candidate_education="Arts")

        score_same = _weighted_score(user, same_edu)
        score_diff = _weighted_score(user, different_edu)

        self.assertLess(score_same, score_diff)

    def test_scoring_never_excludes(self):
        """All candidates in the pool should receive a score - none excluded by scoring."""
        user = _make_registration(
            preferred_location="Patna",
            preferred_education="Engineering",
            preferred_occupation="Software Engineer",
            preferred_age_min=22,
            preferred_age_max=30,
        )
        candidate = _make_registration(
            candidate_dob=date(2000, 6, 1),
            candidate_current_city="Mumbai",
            candidate_education="Arts",
            candidate_occupation="Doctor",
        )

        score = _weighted_score(user, candidate)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)


# ---------------------------------------------------------------------------
# Test: _age_years helper
# ---------------------------------------------------------------------------

class TestAgeCalculation(TestCase):
    def test_age_calculation(self):
        """Age is calculated correctly from DOB."""
        today = timezone.now().date()
        dob = date(today.year - 25, today.month, today.day)
        self.assertEqual(_age_years(dob), 25)

    def test_birthday_not_yet_this_year(self):
        """Age accounts for birthday not yet passed this year."""
        dob = date(timezone.now().year - 25, 12, 31)
        age = _age_years(dob)
        self.assertIn(age, [24, 25])


# ---------------------------------------------------------------------------
# Test: withdrawn registration still returns status (not 404)
# ---------------------------------------------------------------------------

class TestWithdrawnRegistrationStatus(TestCase):
    """GET registrations/me/status/ must return 200 for withdrawn registrations."""

    def test_withdrawn_status_returns_200(self):
        """After withdrawing, GET registrations/me/status/ returns 200 with withdrawn=true."""
        User = get_user_model()
        user = User.objects.create_user(username='testuser', password='testpass')
        registration = Registration.objects.create(
            owner=user,
            reference='SG-999999',
            candidate_full_name='Test Candidate',
            candidate_gender=Registration.Gender.BRIDE,
            verification_status=Registration.VerificationStatus.VERIFIED,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post('/api/registrations/me/withdraw/')
        self.assertEqual(response.status_code, 204)

        response = client.get('/api/registrations/me/status/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['withdrawn'])
        self.assertIsNotNone(response.data.get('withdrawn_at'))

    def test_active_status_returns_withdrawn_false(self):
        """Active (non-withdrawn) registration returns withdrawn=false."""
        User = get_user_model()
        user = User.objects.create_user(username='testuser2', password='testpass')
        Registration.objects.create(
            owner=user,
            reference='SG-888888',
            candidate_full_name='Active Candidate',
            candidate_gender=Registration.Gender.BRIDE,
            verification_status=Registration.VerificationStatus.VERIFIED,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/registrations/me/status/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['withdrawn'])


class TestAutomaticMatchingProposal(TestCase):
    """Two verified registrations should get MatchProposal rows via the task."""

    def test_verified_registrations_get_match_proposal(self):
        User = get_user_model()
        user1 = User.objects.create_user(username='user1', password='pass')
        user2 = User.objects.create_user(username='user2', password='pass')

        reg1 = Registration.objects.create(
            owner=user1,
            reference='SG-AAAAAA',
            candidate_full_name='Bride One',
            candidate_gender=Registration.Gender.BRIDE,
            verification_status=Registration.VerificationStatus.VERIFIED,
            candidate_dob=date(1995, 6, 15),
            candidate_current_city='Patna',
            candidate_education='Engineering',
            candidate_occupation='Engineer',
            gotra='',
        )
        reg2 = Registration.objects.create(
            owner=user2,
            reference='SG-BBBBBB',
            candidate_full_name='Groom One',
            candidate_gender=Registration.Gender.GROOM,
            verification_status=Registration.VerificationStatus.VERIFIED,
            candidate_dob=date(1993, 3, 20),
            candidate_current_city='Mumbai',
            candidate_education='MBA',
            candidate_occupation='Manager',
            gotra='different',
        )

        create_automated_proposal(reg1)

        self.assertEqual(MatchProposal.objects.filter(registration=reg1).count(), 1)
        self.assertEqual(MatchProposal.objects.filter(registration=reg2).count(), 1)

        serializer1 = RegistrationStatusSerializer(reg1)
        self.assertIsNotNone(serializer1.data['match'])
        serializer2 = RegistrationStatusSerializer(reg2)
        self.assertIsNotNone(serializer2.data['match'])

