from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from .models import UserCredentialsBackUP, userPoster
from .services import create_user_with_profile, ensure_user_profile, get_user_profile_by_id
from .views import FORGOT_PASSWORD_HUMAN_ANSWER_SESSION_KEY


@override_settings(SECURE_SSL_REDIRECT=False)
class UserProfileServiceTests(TestCase):
    def test_create_user_with_profile_links_user_and_profile(self):
        user, profile = create_user_with_profile(
            username="profile-user",
            email="profile@example.com",
            password="secret-pass",
            profile_name="Profile User",
            contact="profile@example.com",
            photo="https://example.com/photo.jpg",
            save_password_backup=True,
        )

        user.refresh_from_db()
        profile.refresh_from_db()

        self.assertEqual(user.additionalCreds_id, profile.pk)
        self.assertEqual(user.photoLink, "https://example.com/photo.jpg")
        self.assertEqual(profile.userID, user.pk)
        self.assertEqual(profile.name, "Profile User")
        self.assertEqual(profile.contact, "profile@example.com")
        self.assertTrue(UserCredentialsBackUP.objects.filter(userID=user.pk).exists())

    def test_ensure_user_profile_reuses_legacy_profile(self):
        User = get_user_model()
        user = User.objects.create_user(username="legacy-user", password="secret-pass")
        legacy_profile = userPoster.objects.create(userID=user.pk, name="Legacy User")

        profile = ensure_user_profile(user, contact="legacy@example.com")
        user.refresh_from_db()

        self.assertEqual(profile.pk, legacy_profile.pk)
        self.assertEqual(user.additionalCreds_id, legacy_profile.pk)
        self.assertEqual(profile.contact, "legacy@example.com")
        self.assertEqual(userPoster.objects.filter(userID=user.pk).count(), 1)

    def test_get_user_profile_by_id_ensures_missing_auth_profile(self):
        User = get_user_model()
        user = User.objects.create_user(username="missing-profile", password="secret-pass")

        profile = get_user_profile_by_id(user.pk)
        user.refresh_from_db()

        self.assertEqual(profile.userID, user.pk)
        self.assertEqual(user.additionalCreds_id, profile.pk)
        self.assertEqual(userPoster.objects.filter(userID=user.pk).count(), 1)

    def test_paymongo_user_can_create_first_password_without_current_password(self):
        User = get_user_model()
        user = User.objects.create_user(username="paid@example.com", email="paid@example.com")
        user.set_unusable_password()
        user.save(update_fields=["password"])
        UserCredentialsBackUP.objects.create(userID=user.pk, userPassword="paymongo:txn")
        ensure_user_profile(user, contact="paid@example.com")
        self.client.force_login(user)

        response = self.client.post(
            reverse("userProfile:changepsw"),
            {
                "newPassword": "created-pass-123",
                "newPasswordConfirmation": "created-pass-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("created-pass-123"))
        self.assertEqual(
            UserCredentialsBackUP.objects.get(userID=user.pk).userPassword,
            "created-pass-123",
        )
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(user.pk))

    def test_paymongo_user_profile_shows_create_password_label(self):
        User = get_user_model()
        user = User.objects.create_user(username="label@example.com", email="label@example.com")
        user.set_unusable_password()
        user.save(update_fields=["password"])
        ensure_user_profile(user, contact="label@example.com")
        self.client.force_login(user)

        response = self.client.get(reverse("userProfile:profile"))

        self.assertContains(response, "Create Password")
        self.assertNotContains(response, "Old password")

    def test_forgot_password_rejects_incorrect_human_verification(self):
        self.client.get(reverse("userProfile:profile"))

        with patch("userProfile.views.send_password_reset_email") as send_email:
            response = self.client.post(
                reverse("userProfile:forgotPassword"),
                {
                    "email": "person@example.com",
                    "human_answer": "-1",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please complete the human verification.")
        self.assertContains(response, 'id="forgotPasswordFormWrap" style="display: block;')
        send_email.assert_not_called()

    def test_forgot_password_accepts_correct_human_verification(self):
        User = get_user_model()
        User.objects.create_user(
            username="reset-user",
            email="reset@example.com",
            password="secret-pass",
        )
        self.client.get(reverse("userProfile:profile"))
        human_answer = self.client.session[FORGOT_PASSWORD_HUMAN_ANSWER_SESSION_KEY]

        with patch("userProfile.views.send_password_reset_email", return_value=True) as send_email:
            response = self.client.post(
                reverse("userProfile:forgotPassword"),
                {
                    "email": "reset@example.com",
                    "human_answer": str(human_answer),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "If your email is registered, a password reset link has been sent.",
        )
        send_email.assert_called_once()
