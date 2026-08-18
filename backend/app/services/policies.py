"""Pure authorization policies: easy to audit and test without a database."""


def post_is_visible(*, viewer_id: int, author_id: int, privacy: str, blocked: bool,
                    friends: bool, restricted: bool, follower: bool = False,
                    included: bool = False, excluded: bool = False,
                    custom_base: str = "friends") -> bool:
    if viewer_id == author_id:
        return True
    if blocked:
        return False
    if excluded:
        return False
    if privacy == "public":
        return True
    if restricted:
        return False
    if privacy in {"friends", "friends_except"}:
        return friends and not restricted
    if privacy == "specific_friends":
        return friends and included
    if privacy == "followers":
        return friends or follower
    if privacy == "custom":
        if included:
            return friends
        return custom_base == "public" or (custom_base == "friends" and friends) or (custom_base == "followers" and (friends or follower))
    return False


def friendship_request_can_be_accepted(*, current_user_id: int, addressee_id: int, status: str) -> bool:
    return current_user_id == addressee_id and status == "pending"


def shared_post_is_visible(*, original_visible: bool, shared_copy_visible: bool) -> bool:
    return original_visible and shared_copy_visible


def chat_message_is_valid(*, blocked: bool, message_type: str, content: str, attachment_url: str | None, sticker: str | None) -> bool:
    if blocked or message_type not in {"text", "image", "video", "file", "voice", "sticker", "gif"}:
        return False
    return bool(content.strip() or attachment_url or sticker)
