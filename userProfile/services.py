from django.contrib.auth import get_user_model
from django.db import transaction

from .models import UserCredentialsBackUP, userPoster


DEFAULT_PROFILE_NAME = "Facebook not Connected"


def _has_value(value):
    return value is not None and value != ""


def _profile_name(user, name=None):
    if _has_value(name):
        return str(name).strip() or DEFAULT_PROFILE_NAME

    username = getattr(user, "username", "")
    if username:
        return username

    return DEFAULT_PROFILE_NAME


def _profile_contact(user, contact=None):
    if _has_value(contact):
        return str(contact).strip()

    email = getattr(user, "email", "")
    return email or ""


def _set_profile_value(profile, field_name, value, changed_fields, overwrite=False):
    if not _has_value(value):
        return

    current_value = getattr(profile, field_name)
    if overwrite or not current_value:
        cleaned_value = str(value).strip() if isinstance(value, str) else value
        if current_value != cleaned_value:
            setattr(profile, field_name, cleaned_value)
            changed_fields.append(field_name)


def _set_unique_profile_name(profile, user_id, name, changed_fields, overwrite=False):
    if not _has_value(name):
        return

    cleaned_name = str(name).strip()
    if not cleaned_name:
        return

    if not overwrite and profile.name:
        return

    duplicate_exists = userPoster.objects.filter(
        userID=user_id,
        name=cleaned_name,
    ).exclude(pk=profile.pk).exists()
    if duplicate_exists:
        return

    if profile.name != cleaned_name:
        profile.name = cleaned_name
        changed_fields.append("name")


def _link_user_profile(user, profile, photo=None):
    changed_fields = []

    if getattr(user, "additionalCreds_id", None) != profile.pk:
        user.additionalCreds = profile
        changed_fields.append("additionalCreds")

    if _has_value(photo) and getattr(user, "photoLink", "") != photo:
        user.photoLink = photo
        changed_fields.append("photoLink")

    if changed_fields:
        update_kwargs = {field: getattr(user, field) for field in changed_fields}
        type(user).objects.filter(pk=user.pk).update(**update_kwargs)


@transaction.atomic
def ensure_user_profile(
    user,
    *,
    name=None,
    contact=None,
    photo=None,
    signed_from=None,
    age_range=None,
    gender=None,
    overwrite=False,
):
    """
    Return the canonical userPoster for a UserCredentials row.

    The current schema allows multiple userPoster rows for one auth user, so this
    function first trusts user.additionalCreds, then falls back to the oldest
    profile with the same userID, and only creates a row when no profile exists.
    """
    if user is None or not getattr(user, "pk", None):
        raise ValueError("ensure_user_profile requires a saved user.")

    if getattr(user, "is_authenticated", True) is False:
        raise ValueError("ensure_user_profile requires an authenticated user.")

    user_id = user.pk
    profile = None
    additional_creds_id = getattr(user, "additionalCreds_id", None)

    if additional_creds_id:
        profile = userPoster.objects.select_for_update().filter(
            pk=additional_creds_id,
        ).first()

    if profile is None:
        profile = userPoster.objects.select_for_update().filter(
            userID=user_id,
        ).order_by("id").first()

    if profile is None:
        profile = userPoster.objects.create(
            userID=user_id,
            name=_profile_name(user, name),
            contact=_profile_contact(user, contact),
            photo=photo or "",
            signedFrom=signed_from or "",
            age_range=age_range or "",
            gender=gender or "",
        )
    else:
        changed_fields = []
        if profile.userID != user_id:
            profile.userID = user_id
            changed_fields.append("userID")

        _set_unique_profile_name(profile, user_id, name, changed_fields, overwrite=overwrite)
        _set_profile_value(profile, "contact", contact, changed_fields, overwrite=overwrite)
        _set_profile_value(profile, "photo", photo, changed_fields, overwrite=overwrite)
        _set_profile_value(profile, "signedFrom", signed_from, changed_fields, overwrite=overwrite)
        _set_profile_value(profile, "age_range", age_range, changed_fields, overwrite=overwrite)
        _set_profile_value(profile, "gender", gender, changed_fields, overwrite=overwrite)

        if changed_fields:
            profile.save(update_fields=list(dict.fromkeys(changed_fields)))

    _link_user_profile(user, profile, photo=photo)
    return profile


def ensure_user_profile_by_id(user_id, **profile_kwargs):
    """
    Ensure a profile by auth user id.

    If a matching UserCredentials row exists, the profile is linked back to that
    row. For legacy data without an auth user row, this preserves the previous
    behavior by creating a placeholder userPoster.
    """
    if user_id is None:
        raise ValueError("ensure_user_profile_by_id requires a user id.")

    UserModel = get_user_model()
    auth_user = UserModel.objects.filter(pk=user_id).first()
    if auth_user is not None:
        return ensure_user_profile(auth_user, **profile_kwargs)

    profile = userPoster.objects.filter(userID=user_id).order_by("id").first()
    if profile is not None:
        return profile

    return userPoster.objects.create(
        userID=user_id,
        name=profile_kwargs.get("name") or DEFAULT_PROFILE_NAME,
        contact=profile_kwargs.get("contact") or "",
        photo=profile_kwargs.get("photo") or "",
        signedFrom=profile_kwargs.get("signed_from") or "",
    )


def get_user_profile_by_id(user_id):
    """
    Return the profile for an auth user id, creating it only when the auth user
    exists and is missing a linked profile.
    """
    if user_id is None:
        raise ValueError("get_user_profile_by_id requires a user id.")

    UserModel = get_user_model()
    auth_user = UserModel.objects.filter(pk=user_id).first()
    if auth_user is not None:
        return ensure_user_profile(auth_user)

    profile = userPoster.objects.filter(userID=user_id).order_by("id").first()
    if profile is None:
        raise userPoster.DoesNotExist
    return profile


@transaction.atomic
def create_user_with_profile(
    *,
    username,
    password,
    email="",
    profile_name=None,
    contact=None,
    photo=None,
    signed_from=None,
    age_range=None,
    gender=None,
    save_password_backup=False,
):
    UserModel = get_user_model()
    user = UserModel.objects.create_user(
        username=username,
        email=email or "",
        password=password,
    )
    profile = ensure_user_profile(
        user,
        name=profile_name or username,
        contact=contact if contact is not None else email,
        photo=photo,
        signed_from=signed_from,
        age_range=age_range,
        gender=gender,
        overwrite=True,
    )

    if save_password_backup:
        UserCredentialsBackUP.objects.update_or_create(
            userID=user.pk,
            defaults={"userPassword": password},
        )

    return user, profile
