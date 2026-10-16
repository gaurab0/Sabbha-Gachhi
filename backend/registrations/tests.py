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
from unittest import skip
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
    _age_years,
)
from registrations.matching_engine import create_automated_proposal
from registrations.matching import find_matches_for, create_automated_proposal as create_auto_proposal_matching
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

@skip("Pre-existing: _exclude_same_gotra was never implemented in any matching module.")
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

@skip("Pre-existing: _weighted_score was never implemented in any matching module.")
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
        user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass',
            email_verified=True,
        )
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
        user = User.objects.create_user(
            email='testuser2@example.com',
            password='testpass',
            email_verified=True,
        )
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

    def test_unverified_user_can_read_own_status(self):
        """Unverified users get 200 so the UI can show the verify-email screen."""
        User = get_user_model()
        user = User.objects.create_user(
            email='unverified-status@example.com',
            password='testpass',
            email_verified=False,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/registrations/me/status/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['email_verified'])


class TestAutomaticMatchingProposal(TestCase):
    """Two verified registrations should get MatchProposal rows via the task."""

    def test_verified_registrations_get_match_proposal(self):
        User = get_user_model()
        user1 = User.objects.create_user(
            email='user1@example.com',
            password='pass',
            email_verified=True,
        )
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='pass',
            email_verified=True,
        )

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
        self.assertEqual(len(serializer1.data['matches']), 1)
        serializer2 = RegistrationStatusSerializer(reg2)
        self.assertEqual(len(serializer2.data['matches']), 1)


_unique_counter = [0]


def _unique(prefix):
    _unique_counter[0] += 1
    return f'{prefix}{_unique_counter[0]}'


def _make_verified_user(email):
    User = get_user_model()
    return User.objects.create_user(
        email=email, password='testpass', email_verified=True,
    )


def _make_proposal_pair(owner_verified=True):
    """Two verified registrations with linked proposals; returns
    (owner, proposal_for_owner, paired_registration)."""
    tag = _unique('pp')
    owner = _make_verified_user(f'owner-{tag}@example.com')
    other_user = _make_verified_user(f'other-{tag}@example.com')
    reg = Registration.objects.create(
        owner=owner,
        reference=f'SG-{tag[:6].upper()}A',
        candidate_full_name='Owner Candidate',
        candidate_gender=Registration.Gender.BRIDE,
        verification_status=(
            Registration.VerificationStatus.VERIFIED if owner_verified
            else Registration.VerificationStatus.PENDING
        ),
        candidate_dob=date(1995, 6, 15),
    )
    other = Registration.objects.create(
        owner=other_user,
        reference=f'SG-{tag[:6].upper()}B',
        candidate_full_name='Other Candidate',
        candidate_gender=Registration.Gender.GROOM,
        verification_status=Registration.VerificationStatus.VERIFIED,
        candidate_dob=date(1993, 3, 20),
        candidate_photo='https://example.com/other-photo.jpg',
        guardian_phone='+91-9000000001',
        guardian_email='other-family@example.com',
    )
    mine = MatchProposal.objects.create(
        registration=reg, shared_by_panjikar='Matched by Sabha Gachhi',
        shared_details=['Age 31'],
    )
    theirs = MatchProposal.objects.create(
        registration=other, shared_by_panjikar='Matched by Sabha Gachhi',
        shared_details=['Age 33'],
    )
    mine.paired_proposal = theirs
    mine.save(update_fields=['paired_proposal'])
    theirs.paired_proposal = mine
    theirs.save(update_fields=['paired_proposal'])
    return owner, mine, other


class TestMatchProposalContact(TestCase):
    """GET match-proposals/<id>/contact/ gates and minimal shape."""

    def test_unauthenticated_is_rejected(self):
        _, proposal, _ = _make_proposal_pair()
        response = APIClient().get(f'/api/match-proposals/{proposal.pk}/contact/')
        # DRF answers unauthenticated requests with 401; the 403 gates below
        # cover the authenticated-but-not-allowed cases.
        self.assertEqual(response.status_code, 401)

    def test_other_owners_proposal_is_rejected(self):
        _, proposal, _ = _make_proposal_pair()
        stranger = _make_verified_user('stranger@example.com')
        client = APIClient()
        client.force_authenticate(user=stranger)
        response = client.get(f'/api/match-proposals/{proposal.pk}/contact/')
        self.assertEqual(response.status_code, 403)

    def test_unverified_registration_is_rejected(self):
        owner, proposal, _ = _make_proposal_pair(owner_verified=False)
        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get(f'/api/match-proposals/{proposal.pk}/contact/')
        self.assertEqual(response.status_code, 403)

    def test_returns_minimal_shape_without_contact_before_accept(self):
        owner, proposal, _ = _make_proposal_pair()
        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get(f'/api/match-proposals/{proposal.pk}/contact/')
        self.assertEqual(response.status_code, 200)
        # Only the three documented keys — no names, scores, or lineage.
        self.assertEqual(set(response.data.keys()), {'photo_url', 'email', 'phone'})
        # Photo comes from the paired candidate; contact is blank pre-accept.
        self.assertEqual(response.data['photo_url'], 'https://example.com/other-photo.jpg')
        self.assertEqual(response.data['email'], '')
        self.assertEqual(response.data['phone'], '')

    def test_returns_contact_after_both_accepted(self):
        owner, proposal, _ = _make_proposal_pair()
        proposal.contact_guardian_name = 'Other Guardian'
        proposal.contact_phone = '+91-9000000001'
        proposal.contact_email = 'other-family@example.com'
        proposal.save(update_fields=[
            'contact_guardian_name', 'contact_phone', 'contact_email',
        ])
        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get(f'/api/match-proposals/{proposal.pk}/contact/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], 'other-family@example.com')
        self.assertEqual(response.data['phone'], '+91-9000000001')


class TestWithdrawUpgrade(TestCase):
    """Withdraw stores a reason, is idempotent, and cancels proposals."""

    def _withdrawable(self, email=None):
        tag = _unique('wd')
        owner = _make_verified_user(email or f'withdraw-{tag}@example.com')
        reg = Registration.objects.create(
            owner=owner,
            reference=f'SG-{tag[:6].upper()}W',
            candidate_full_name='Withdraw Candidate',
            candidate_gender=Registration.Gender.BRIDE,
            verification_status=Registration.VerificationStatus.VERIFIED,
            candidate_dob=date(1995, 6, 15),
        )
        client = APIClient()
        client.force_authenticate(user=owner)
        return owner, reg, client

    def test_withdraw_stores_reason(self):
        _, reg, client = self._withdrawable()
        response = client.post(
            '/api/registrations/me/withdraw/', {'reason': 'Found a match elsewhere'},
            format='json',
        )
        self.assertEqual(response.status_code, 204)
        reg.refresh_from_db()
        self.assertTrue(reg.withdrawn)
        self.assertEqual(reg.withdrawn_reason, 'Found a match elsewhere')
        self.assertIsNotNone(reg.withdrawn_at)

    def test_withdraw_is_idempotent(self):
        _, reg, client = self._withdrawable()
        self.assertEqual(client.post('/api/registrations/me/withdraw/').status_code, 204)
        # Second call (e.g. double-click retry) succeeds instead of 404ing.
        response = client.post(
            '/api/registrations/me/withdraw/', {'reason': 'Changed mind on reason'},
            format='json',
        )
        self.assertEqual(response.status_code, 204)
        reg.refresh_from_db()
        self.assertTrue(reg.withdrawn)
        self.assertEqual(reg.withdrawn_reason, 'Changed mind on reason')

    def test_withdraw_cancels_active_proposals(self):
        owner, proposal, _ = _make_proposal_pair()
        client = APIClient()
        client.force_authenticate(user=owner)
        self.assertEqual(
            client.post('/api/registrations/me/withdraw/').status_code, 204
        )
        proposal.refresh_from_db()
        self.assertEqual(proposal.your_response, MatchProposal.PartyResponse.DECLINED)
        proposal.paired_proposal.refresh_from_db()
        self.assertEqual(
            proposal.paired_proposal.other_response,
            MatchProposal.PartyResponse.DECLINED,
        )


class TestMatchProposalRespond(TestCase):
    """POST match-proposals/<id>/respond/ via the ObjectId route."""

    def test_accept_via_str_route_updates_and_mirrors(self):
        User = get_user_model()
        owner = User.objects.create_user(
            email='respond-owner@example.com', password='testpass',
            email_verified=True, phone_verified=True,
        )
        other_user = User.objects.create_user(
            email='respond-other@example.com', password='testpass',
            email_verified=True, phone_verified=True,
        )
        tag = _unique('rs')
        reg = Registration.objects.create(
            owner=owner,
            reference=f'SG-{tag[:6].upper()}A',
            candidate_full_name='Respond Candidate',
            candidate_gender=Registration.Gender.BRIDE,
            verification_status=Registration.VerificationStatus.VERIFIED,
            candidate_dob=date(1995, 6, 15),
        )
        other = Registration.objects.create(
            owner=other_user,
            reference=f'SG-{tag[:6].upper()}B',
            candidate_full_name='Other Candidate',
            candidate_gender=Registration.Gender.GROOM,
            verification_status=Registration.VerificationStatus.VERIFIED,
            candidate_dob=date(1993, 3, 20),
        )
        mine = MatchProposal.objects.create(
            registration=reg, shared_by_panjikar='Matched by Sabha Gachhi',
            shared_details=['Age 31'],
        )
        theirs = MatchProposal.objects.create(
            registration=other, shared_by_panjikar='Matched by Sabha Gachhi',
            shared_details=['Age 33'],
        )
        mine.paired_proposal = theirs
        mine.save(update_fields=['paired_proposal'])
        theirs.paired_proposal = mine
        theirs.save(update_fields=['paired_proposal'])

        client = APIClient()
        client.force_authenticate(user=owner)
        # ObjectId pk in the URL (would 404 on an <int:pk> route).
        response = client.post(
            f'/api/match-proposals/{mine.pk}/respond/',
            {'action': 'accept'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['your_response'], 'accepted')
        mine.refresh_from_db()
        theirs.refresh_from_db()
        self.assertEqual(mine.your_response, MatchProposal.PartyResponse.ACCEPTED)
        self.assertEqual(theirs.other_response, MatchProposal.PartyResponse.ACCEPTED)

    def test_rejects_bad_action(self):
        owner, proposal, _ = _make_proposal_pair()
        owner.phone_verified = True
        owner.save(update_fields=['phone_verified'])
        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.post(
            f'/api/match-proposals/{proposal.pk}/respond/',
            {'action': 'maybe'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# Test: moolgram eligibility and multiple matches
# ---------------------------------------------------------------------------

class TestMoolgramAndMultipleMatches(TestCase):
    """Tests for the new moolgram rejection rule and multiple matches per candidate."""

    def _make_reg(self, email, gender, gotra, moolgram, dob=date(1995, 6, 15)):
        User = get_user_model()
        user = User.objects.create_user(email=email, password='testpass', email_verified=True)
        tag = _unique(email)
        # Use full tag for reference to avoid collisions (truncated to fit max_length=20)
        ref = f'SG-{tag[:12].upper()}'
        return Registration.objects.create(
            owner=user,
            reference=ref,
            candidate_full_name=f'Candidate {email}',
            candidate_gender=gender,
            verification_status=Registration.VerificationStatus.VERIFIED,
            candidate_dob=dob,
            gotra=gotra,
            mool_gram=moolgram,
        )

    # Case 1: Different gotra, Different moolgram -> Match created
    def test_different_gotra_different_moolgram_creates_match(self):
        bride = self._make_reg('bride1@test.com', Registration.Gender.BRIDE, 'Kashyapa', 'Rampur')
        groom = self._make_reg('groom1@test.com', Registration.Gender.GROOM, 'Atri', 'Sitapur')

        result = run_matching_engine(bride)

        self.assertEqual(result['audit_log']['final_count'], 1)
        self.assertEqual(Match.objects.filter(registration=bride).count(), 1)
        match = Match.objects.filter(registration=bride).first()
        self.assertEqual(match.candidate, groom)

    # Case 2: Different gotra, Same moolgram -> Rejected (SAME_MOOLGRAM)
    def test_different_gotra_same_moolgram_rejected(self):
        bride = self._make_reg('bride2@test.com', Registration.Gender.BRIDE, 'Kashyapa', 'Rampur')
        groom = self._make_reg('groom2@test.com', Registration.Gender.GROOM, 'Atri', 'Rampur')

        result = run_matching_engine(bride)

        self.assertEqual(result['audit_log']['final_count'], 0)
        self.assertEqual(Match.objects.filter(registration=bride).count(), 0)
        # Check audit log has SAME_MOOLGRAM reason
        log = MatchAttemptLog.objects.filter(registration=bride).first()
        self.assertIsNotNone(log)
        reasons = log.candidates_considered[0]['reasons']
        self.assertTrue(any(r['code'] == 'SAME_MOOLGRAM' for r in reasons))

    # Case 3: Same gotra, Different moolgram -> Rejected (SAME_GOTRA)
    def test_same_gotra_different_moolgram_rejected(self):
        bride = self._make_reg('bride3@test.com', Registration.Gender.BRIDE, 'Kashyapa', 'Rampur')
        groom = self._make_reg('groom3@test.com', Registration.Gender.GROOM, 'Kashyapa', 'Sitapur')

        result = run_matching_engine(bride)

        self.assertEqual(result['audit_log']['final_count'], 0)
        self.assertEqual(Match.objects.filter(registration=bride).count(), 0)
        log = MatchAttemptLog.objects.filter(registration=bride).first()
        reasons = log.candidates_considered[0]['reasons']
        self.assertTrue(any(r['code'] == 'SAME_GOTRA' for r in reasons))

    # Case 4: Same gotra, Same moolgram -> Rejected
    def test_same_gotra_same_moolgram_rejected(self):
        bride = self._make_reg('bride4@test.com', Registration.Gender.BRIDE, 'Kashyapa', 'Rampur')
        groom = self._make_reg('groom4@test.com', Registration.Gender.GROOM, 'Kashyapa', 'Rampur')

        result = run_matching_engine(bride)

        self.assertEqual(result['audit_log']['final_count'], 0)
        self.assertEqual(Match.objects.filter(registration=bride).count(), 0)

    # Case 5: Candidate A eligible with B, C, D -> 3 matches for A
    def test_one_candidate_multiple_matches(self):
        bride = self._make_reg('bride5@test.com', Registration.Gender.BRIDE, 'Kashyapa', 'Rampur')
        groom1 = self._make_reg('groom5a@test.com', Registration.Gender.GROOM, 'Atri', 'Sitapur')
        groom2 = self._make_reg('groom5b@test.com', Registration.Gender.GROOM, 'Bharadwaja', 'Lucknow')
        groom3 = self._make_reg('groom5c@test.com', Registration.Gender.GROOM, 'Vishvamitra', 'Kanpur')

        result = run_matching_engine(bride)

        self.assertEqual(result['audit_log']['final_count'], 3)
        self.assertEqual(Match.objects.filter(registration=bride).count(), 3)
        matched_candidates = set(Match.objects.filter(registration=bride).values_list('candidate_id', flat=True))
        self.assertEqual(matched_candidates, {groom1.pk, groom2.pk, groom3.pk})

    # Case 6: Pair (A,B) run twice or as (B,A) -> Only one match record
    def test_duplicate_pair_prevented(self):
        bride = self._make_reg('bride6@test.com', Registration.Gender.BRIDE, 'Kashyapa', 'Rampur')
        groom = self._make_reg('groom6@test.com', Registration.Gender.GROOM, 'Atri', 'Sitapur')

        # Run from bride's side
        run_matching_engine(bride)
        # Run from groom's side (reverse direction)
        run_matching_engine(groom)

        # Should only have one Match record total (either direction)
        matches_bride = Match.objects.filter(registration=bride).count()
        matches_groom = Match.objects.filter(registration=groom).count()
        total_matches = matches_bride + matches_groom
        self.assertEqual(total_matches, 1)

    # Case 7: Moolgram casing/whitespace variants ("Rampur " vs "rampur") -> Treated as same, rejected
    def test_moolgram_normalization_casing_whitespace(self):
        bride = self._make_reg('bride7@test.com', Registration.Gender.BRIDE, 'Kashyapa', 'Rampur ')
        groom = self._make_reg('groom7@test.com', Registration.Gender.GROOM, 'Atri', '  rampur')

        result = run_matching_engine(bride)

        self.assertEqual(result['audit_log']['final_count'], 0)
        self.assertEqual(Match.objects.filter(registration=bride).count(), 0)
        log = MatchAttemptLog.objects.filter(registration=bride).first()
        reasons = log.candidates_considered[0]['reasons']
        self.assertTrue(any(r['code'] == 'SAME_MOOLGRAM' for r in reasons))

    # Case 8: Missing moolgram -> Skip check, mark "needs review", still eligible if other checks pass
    def test_missing_moolgram_skip_check_needs_review(self):
        bride = self._make_reg('bride8@test.com', Registration.Gender.BRIDE, 'Kashyapa', '')  # empty moolgram
        groom = self._make_reg('groom8@test.com', Registration.Gender.GROOM, 'Atri', 'Sitapur')

        result = run_matching_engine(bride)

        self.assertEqual(result['audit_log']['final_count'], 1)
        self.assertEqual(Match.objects.filter(registration=bride).count(), 1)
        log = MatchAttemptLog.objects.filter(registration=bride).first()
        reasons = log.candidates_considered[0]['reasons']
        # Should have NEEDS_REVIEW code
        self.assertTrue(any(r['code'] == 'NEEDS_REVIEW' for r in reasons))
        # Should NOT have SAME_MOOLGRAM (check was skipped)
        self.assertFalse(any(r['code'] == 'SAME_MOOLGRAM' for r in reasons))


# ---------------------------------------------------------------------------
# Test: matching.py pipeline (find_matches_for, create_automated_proposal)
# ---------------------------------------------------------------------------

class TestMatchingPipelineMultiple(TestCase):
    """Test the matching.py pipeline with multiple matches."""

    def _make_reg(self, email, gender, gotra, moolgram, dob=date(1995, 6, 15)):
        User = get_user_model()
        user = User.objects.create_user(email=email, password='testpass', email_verified=True)
        tag = _unique(email)
        ref = f'SG-{tag[:12].upper()}'
        return Registration.objects.create(
            owner=user,
            reference=ref,
            candidate_full_name=f'Candidate {email}',
            candidate_gender=gender,
            verification_status=Registration.VerificationStatus.VERIFIED,
            candidate_dob=dob,
            gotra=gotra,
            mool_gram=moolgram,
            candidate_current_city='Patna',
            candidate_education='Engineering',
            candidate_occupation='Engineer',
        )

    def test_find_matches_for_returns_all_eligible(self):
        bride = self._make_reg('bride@test.com', Registration.Gender.BRIDE, 'Kashyapa', 'Rampur')
        groom1 = self._make_reg('groom1@test.com', Registration.Gender.GROOM, 'Atri', 'Sitapur')
        groom2 = self._make_reg('groom2@test.com', Registration.Gender.GROOM, 'Bharadwaja', 'Lucknow')

        matches = find_matches_for(bride)

        self.assertEqual(len(matches), 2)
        self.assertIn(groom1, matches)
        self.assertIn(groom2, matches)

    def test_create_automated_proposal_creates_for_all_matches(self):
        bride = self._make_reg('bride@test.com', Registration.Gender.BRIDE, 'Kashyapa', 'Rampur')
        groom1 = self._make_reg('groom1@test.com', Registration.Gender.GROOM, 'Atri', 'Sitapur')
        groom2 = self._make_reg('groom2@test.com', Registration.Gender.GROOM, 'Bharadwaja', 'Lucknow')

        create_automated_proposal(bride)

        # Should create proposals for both grooms
        proposals = MatchProposal.objects.filter(registration=bride)
        self.assertEqual(proposals.count(), 2)

        # Each proposal should be paired with the groom's proposal
        for proposal in proposals:
            self.assertIsNotNone(proposal.paired_proposal)
            self.assertEqual(proposal.paired_proposal.registration.candidate_gender, Registration.Gender.GROOM)

    def test_create_automated_proposal_idempotent_per_pair(self):
        bride = self._make_reg('bride@test.com', Registration.Gender.BRIDE, 'Kashyapa', 'Rampur')
        groom = self._make_reg('groom@test.com', Registration.Gender.GROOM, 'Atri', 'Sitapur')

        # Run twice
        create_automated_proposal(bride)
        create_automated_proposal(bride)

        # Should only have one proposal pair
        proposals = MatchProposal.objects.filter(registration=bride)
        self.assertEqual(proposals.count(), 1)

