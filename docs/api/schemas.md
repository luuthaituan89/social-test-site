# SocialN API — Data schemas

> Data dictionary sinh từ OpenAPI. Tổng cộng **58 schemas**. Trường có dấu `*` là bắt buộc.

## `AccountPasswordConfirm`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `password` | `string` | Có | minLength=1; maxLength=128 |

## `ActiveStatusUpdate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `enabled` | `boolean` | Có | — |

## `ActivityDeleteRequest`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `category` | `string` | Có | enum: search, login, posts, profile, friends, security, all |
| `date_from` | `string` | Không | — |
| `date_to` | `string` | Không | — |

## `AlbumCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `name` | `string` | Có | minLength=1; maxLength=150 |
| `description` | `string` | Không | — |
| `privacy` | `string` | Không | default='friends' |
| `audience` | `AudienceConfig` | Không | — |

## `AudienceConfig`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `included_ids` | `integer[]` | Không | — |
| `excluded_ids` | `integer[]` | Không | — |
| `base` | `string` | Không | default='friends'; enum: public, friends, followers |

## `Body_avatar_api_users_me_avatar_post`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `file` | `string` | Có | format=binary |

## `Body_cover_api_users_me_cover_post`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `file` | `string` | Có | format=binary |

## `Body_upload_album_media_api_albums__album_id__media_post`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `file` | `string` | Có | format=binary |
| `caption` | `string` | Không | default='' |

## `Body_upload_api_upload_post`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `file` | `string` | Có | format=binary |

## `Body_upload_chat_file_api_chat_upload_post`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `file` | `string` | Có | format=binary |

## `ChatGroupCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `name` | `string` | Có | minLength=1; maxLength=120 |
| `member_ids` | `integer[]` | Không | — |
| `require_admin_approval` | `boolean` | Không | default=False |
| `first_message` | `MessageCreate` | Có | — |

## `ChatGroupUpdate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `name` | `string` | Có | minLength=1; maxLength=120 |
| `require_admin_approval` | `boolean` | Không | default=False |
| `avatar_url` | `string` | Không | — |
| `theme` | `string` | Không | default='default'; maxLength=40 |
| `quick_reaction` | `string` | Không | default='👍'; maxLength=20 |
| `invite_enabled` | `boolean` | Không | default=True |
| `member_customization` | `boolean` | Không | default=False |

## `ChatPollCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `question` | `string` | Có | minLength=1; maxLength=500 |
| `options` | `string[]` | Có | — |

## `CommentCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `content` | `string` | Có | minLength=1; maxLength=2000 |

## `ConversationDraftIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `content` | `string` | Không | default=''; maxLength=5000 |

## `DataExportRequest`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `format` | `string` | Không | default='json'; enum: json, html |
| `categories` | `string[]` | Không | — |
| `date_from` | `string` | Không | — |
| `date_to` | `string` | Không | — |

## `DirectChatUpdate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `theme` | `string` | Không | default='default'; maxLength=40 |
| `quick_reaction` | `string` | Không | default='👍'; maxLength=20 |
| `my_nickname` | `string` | Không | — |
| `other_nickname` | `string` | Không | — |
| `word_effects` | `object` | Không | — |
| `disappearing_seconds` | `integer` | Không | default=0; minimum=0.0; maximum=86400.0 |
| `mute_minutes` | `integer` | Không | default=0; minimum=-1.0; maximum=525600.0 |
| `restricted` | `boolean` | Không | default=False |

## `EventCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `title` | `string` | Có | minLength=2; maxLength=200 |
| `description` | `string` | Không | — |
| `cover_url` | `string` | Không | — |
| `location_name` | `string` | Không | — |
| `latitude` | `number` | Không | — |
| `longitude` | `number` | Không | — |
| `starts_at` | `string` | Có | format=date-time |
| `ends_at` | `string` | Không | — |
| `privacy` | `string` | Không | default='public'; enum: public, private |
| `group_id` | `integer` | Không | — |
| `page_id` | `integer` | Không | — |

## `EventResponseIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `response` | `string` | Có | enum: going, interested, not_going |

## `FeedAuthorPreferenceIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `favorite` | `boolean` | Không | — |
| `snooze_days` | `integer` | Không | — |

## `GroupCommentCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `content` | `string` | Có | minLength=1; maxLength=2000 |

## `GroupCoverUpdate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `cover_url` | `string` | Có | minLength=1; maxLength=500 |

## `GroupCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `name` | `string` | Có | minLength=2; maxLength=150 |
| `description` | `string` | Không | — |
| `rules` | `string` | Không | — |
| `privacy` | `string` | Không | default='public' |
| `visibility` | `string` | Không | default='visible' |
| `group_type` | `string` | Không | default='general' |
| `cover_url` | `string` | Không | — |
| `approval_questions` | `string[]` | Không | — |

## `GroupJoinIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `answers` | `string[]` | Không | — |

## `GroupPostCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `content` | `string` | Không | default=''; maxLength=10000 |
| `media_url` | `string` | Không | — |
| `media_type` | `string` | Không | default='image' |
| `is_anonymous` | `boolean` | Không | default=False |

## `GroupReportCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `reason` | `string` | Có | minLength=3; maxLength=500 |

## `GroupUpdate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `name` | `string` | Có | minLength=2; maxLength=150 |
| `description` | `string` | Không | — |
| `rules` | `string` | Không | — |
| `privacy` | `string` | Không | default='public' |
| `visibility` | `string` | Không | default='visible' |
| `cover_url` | `string` | Không | — |
| `approval_questions` | `string[]` | Không | — |
| `allow_anonymous_posts` | `boolean` | Không | default=True |
| `require_post_approval` | `boolean` | Không | default=False |

## `HTTPValidationError`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `detail` | `ValidationError[]` | Không | — |

## `LoginIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `email` | `string` | Có | format=email |
| `password` | `string` | Có | — |

## `LoginResult`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `access_token` | `string` | Không | — |
| `token_type` | `string` | Không | default='bearer' |
| `user` | `UserPublic` | Không | — |
| `expires_in` | `integer` | Không | default=900 |
| `requires_2fa` | `boolean` | Không | default=False |
| `challenge_token` | `string` | Không | — |
| `verification_required` | `boolean` | Không | default=False |

## `MarketplaceCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `title` | `string` | Có | minLength=2; maxLength=180 |
| `description` | `string` | Không | — |
| `price_minor` | `integer` | Không | default=0; minimum=0.0 |
| `currency` | `string` | Không | default='VND'; minLength=3; maxLength=3 |
| `condition` | `string` | Không | default='used'; enum: new, like_new, good, fair, used |
| `location_name` | `string` | Không | — |
| `media_url` | `string` | Không | — |

## `MessageCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `content` | `string` | Không | default=''; maxLength=5000 |
| `message_type` | `string` | Không | default='text' |
| `attachment_url` | `string` | Không | — |
| `attachment_name` | `string` | Không | — |
| `attachment_mime` | `string` | Không | — |
| `sticker` | `string` | Không | — |
| `reply_to_id` | `integer` | Không | — |
| `view_once` | `boolean` | Không | default=False |

## `MessageEditIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `content` | `string` | Có | minLength=1; maxLength=5000 |

## `NotificationPreferenceIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `category` | `string` | Có | enum: messages, friend_requests, comments, reactions, groups, security, other |
| `in_app` | `boolean` | Không | default=True |
| `web_push` | `boolean` | Không | default=True |
| `email` | `boolean` | Không | default=False |

## `PageCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `name` | `string` | Có | minLength=2; maxLength=150 |
| `slug` | `string` | Có | minLength=3; maxLength=100; pattern=^[a-z0-9][a-z0-9-]*$ |
| `category` | `string` | Không | default='community'; minLength=2; maxLength=80 |
| `description` | `string` | Không | — |
| `avatar_url` | `string` | Không | — |
| `cover_url` | `string` | Không | — |

## `PasswordChange`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `current_password` | `string` | Có | — |
| `new_password` | `string` | Có | minLength=8; maxLength=128 |

## `PasswordConfirm`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `password` | `string` | Có | minLength=1; maxLength=128 |

## `PasswordResetConfirm`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `token` | `string` | Có | minLength=32; maxLength=300 |
| `new_password` | `string` | Có | minLength=8; maxLength=128 |

## `PasswordResetRequest`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `email` | `string` | Có | format=email |

## `PostCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `content` | `string` | Không | default='' |
| `privacy` | `string` | Không | default='public' |
| `image_url` | `string` | Không | — |
| `media_type` | `string` | Không | — |
| `sticker` | `string` | Không | — |
| `audience` | `AudienceConfig` | Không | — |

## `PostShareIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `destination` | `string` | Không | default='feed' |
| `caption` | `string` | Không | default=''; maxLength=5000 |
| `privacy` | `string` | Không | default='public' |
| `target_id` | `integer` | Không | — |
| `target_type` | `string` | Không | — |
| `audience` | `AudienceConfig` | Không | — |

## `PrivacySettingsUpdate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `dob` | `ProfileFieldPrivacy` | Có | — |
| `hometown` | `ProfileFieldPrivacy` | Có | — |
| `relationship` | `ProfileFieldPrivacy` | Có | — |
| `albums` | `ProfileFieldPrivacy` | Có | — |
| `friends_list` | `ProfileFieldPrivacy` | Có | — |

## `ProfileFieldPrivacy`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `included_ids` | `integer[]` | Không | — |
| `excluded_ids` | `integer[]` | Không | — |
| `base` | `string` | Không | default='friends'; enum: public, friends, followers |
| `audience` | `string` | Không | default='friends'; enum: public, friends, friends_except, specific_friends, followers, custom, only_me |

## `ProfileUpdate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `name` | `string` | Không | — |
| `dob` | `string` | Không | — |
| `hometown` | `string` | Không | — |
| `gender` | `string` | Không | — |
| `relationship_status` | `string` | Không | — |
| `relationship_partner_id` | `integer` | Không | — |
| `relationship_since` | `string` | Không | — |
| `bio` | `string` | Không | — |

## `PushSubscriptionIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `endpoint` | `string` | Có | minLength=10; maxLength=4000 |
| `p256dh` | `string` | Có | minLength=1; maxLength=255 |
| `auth` | `string` | Có | minLength=1; maxLength=255 |

## `ReactionIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `reaction` | `string` | Không | default='like' |

## `ReelCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `caption` | `string` | Không | default=''; maxLength=2200 |
| `video_url` | `string` | Có | minLength=1; maxLength=500 |
| `thumbnail_url` | `string` | Không | — |
| `privacy` | `string` | Không | default='public'; enum: public, friends, friends_except, specific_friends, followers, custom, only_me |
| `audience` | `AudienceConfig` | Không | — |

## `RegisterIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `email` | `string` | Có | format=email |
| `username` | `string` | Có | minLength=3; maxLength=80 |
| `name` | `string` | Có | minLength=1; maxLength=120 |
| `password` | `string` | Có | minLength=8; maxLength=128 |

## `SavePostIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `collection_id` | `integer` | Không | — |

## `SavedCollectionIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `name` | `string` | Có | minLength=1; maxLength=120 |

## `StoryCreate`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `content` | `string` | Không | default=''; maxLength=1000 |
| `media_url` | `string` | Có | minLength=1; maxLength=500 |
| `media_type` | `string` | Không | default='image'; enum: image, video |
| `privacy` | `string` | Không | default='friends'; enum: public, friends, friends_except, specific_friends, followers, custom, only_me |
| `audience` | `AudienceConfig` | Không | — |

## `TokenConfirm`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `token` | `string` | Có | minLength=32; maxLength=300 |

## `TokenOut`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `access_token` | `string` | Có | — |
| `token_type` | `string` | Không | default='bearer' |
| `user` | `UserPublic` | Có | — |
| `expires_in` | `integer` | Không | default=900 |
| `verification_required` | `boolean` | Không | default=False |

## `TwoFactorConfirm`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `code` | `string` | Có | minLength=6; maxLength=20 |

## `TwoFactorLoginIn`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `challenge_token` | `string` | Có | — |
| `code` | `string` | Có | minLength=6; maxLength=20 |

## `UserPublic`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `id` | `integer` | Có | — |
| `username` | `string` | Có | — |
| `name` | `string` | Có | — |
| `dob` | `string` | Không | — |
| `hometown` | `string` | Không | — |
| `gender` | `string` | Không | — |
| `relationship_status` | `string` | Không | — |
| `relationship_partner_id` | `integer` | Không | — |
| `relationship_since` | `string` | Không | — |
| `bio` | `string` | Không | — |
| `avatar_url` | `string` | Không | — |
| `cover_url` | `string` | Không | — |
| `active_status_enabled` | `boolean` | Không | default=True |
| `account_status` | `string` | Không | default='active' |
| `email_verified` | `boolean` | Không | default=False |
| `two_factor_enabled` | `boolean` | Không | default=False |

## `UsernameChange`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `username` | `string` | Có | minLength=3; maxLength=80 |

## `ValidationError`

| Field | Type | Required | Validation / default / description |
|---|---|:---:|---|
| `loc` | `string \| integer[]` | Có | — |
| `msg` | `string` | Có | — |
| `type` | `string` | Có | — |

