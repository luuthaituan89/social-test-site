import pytest

from app.services.policies import (
    chat_message_is_valid,
    friendship_request_can_be_accepted,
    post_is_visible,
    shared_post_is_visible,
)


@pytest.mark.parametrize("privacy,friends,restricted,expected", [
    ("public", False, False, True),
    ("friends", True, False, True),
    ("friends", True, True, False),
    ("only_me", True, False, False),
])
def test_post_privacy_overlap(privacy, friends, restricted, expected):
    assert post_is_visible(viewer_id=2, author_id=1, privacy=privacy, blocked=False, friends=friends, restricted=restricted) is expected
    assert post_is_visible(viewer_id=2, author_id=1, privacy=privacy, blocked=True, friends=friends, restricted=restricted) is False


def test_advanced_post_audiences():
    common = {"viewer_id": 2, "author_id": 1, "blocked": False, "restricted": False}
    assert post_is_visible(**common, privacy="friends_except", friends=True, excluded=False)
    assert not post_is_visible(**common, privacy="friends_except", friends=True, excluded=True)
    assert post_is_visible(**common, privacy="specific_friends", friends=True, included=True)
    assert not post_is_visible(**common, privacy="specific_friends", friends=True, included=False)
    assert post_is_visible(**common, privacy="followers", friends=False, follower=True)
    assert post_is_visible(**common, privacy="custom", friends=True, included=True)
    assert not post_is_visible(**common, privacy="custom", friends=False, included=True)
    assert not post_is_visible(**common, privacy="custom", friends=False, included=False, custom_base="friends")


def test_restricted_user_only_sees_public_audience():
    assert post_is_visible(viewer_id=2, author_id=1, privacy="public", blocked=False, friends=True, restricted=True)
    assert not post_is_visible(viewer_id=2, author_id=1, privacy="followers", blocked=False, friends=True, follower=True, restricted=True)


def test_friend_request_only_addressee_can_accept_pending_request():
    assert friendship_request_can_be_accepted(current_user_id=2, addressee_id=2, status="pending")
    assert not friendship_request_can_be_accepted(current_user_id=1, addressee_id=2, status="pending")
    assert not friendship_request_can_be_accepted(current_user_id=2, addressee_id=2, status="accepted")


def test_shared_post_requires_both_privacy_layers():
    assert shared_post_is_visible(original_visible=True, shared_copy_visible=True)
    assert not shared_post_is_visible(original_visible=False, shared_copy_visible=True)
    assert not shared_post_is_visible(original_visible=True, shared_copy_visible=False)


def test_chat_policy_rejects_blocked_and_empty_messages():
    assert chat_message_is_valid(blocked=False, message_type="text", content="hello", attachment_url=None, sticker=None)
    assert chat_message_is_valid(blocked=False, message_type="image", content="", attachment_url="/media/a.jpg", sticker=None)
    assert not chat_message_is_valid(blocked=True, message_type="text", content="hello", attachment_url=None, sticker=None)
    assert not chat_message_is_valid(blocked=False, message_type="text", content="  ", attachment_url=None, sticker=None)
