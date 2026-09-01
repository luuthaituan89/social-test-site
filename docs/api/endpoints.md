# SocialN API — Danh mục endpoint

> Sinh từ OpenAPI 2.0.0. Tổng cộng **175 REST operations** trên **145 paths**.

Quy ước: **Có** trong cột Auth nghĩa là gửi `Authorization: Bearer {{token}}`. `Input` liệt kê path/query/header và request body.

## Account data lifecycle

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `DELETE` | `/api/account/activity`<br><small>Clear Activity</small> | Có | body application/json: `ActivityDeleteRequest` | `200` |
| `POST` | `/api/account/deactivate`<br><small>Deactivate</small> | Có | body application/json: `AccountPasswordConfirm` | `200` |
| `POST` | `/api/account/delete`<br><small>Schedule Deletion</small> | Có | body application/json: `AccountPasswordConfirm` | `200` |
| `POST` | `/api/account/export`<br><small>Export Data</small> | Có | body application/json: `DataExportRequest` | `200` |
| `GET` | `/api/account/lifecycle`<br><small>Lifecycle</small> | Có | — | `200` |

## Activity log

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/api/activity`<br><small>Activity Log</small> | Có | query `category`: string; query `limit`: integer; query `offset`: integer | `200` |

## Albums

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `POST` | `/api/albums`<br><small>Create Album</small> | Có | body application/json: `AlbumCreate` | `200` |
| `GET` | `/api/albums/user/{user_id}`<br><small>List Albums</small> | Có | path `user_id`*: integer | `200` |
| `DELETE` | `/api/albums/{album_id}`<br><small>Delete Album</small> | Có | path `album_id`*: integer | `200` |
| `GET` | `/api/albums/{album_id}`<br><small>Get Album</small> | Có | path `album_id`*: integer | `200` |
| `PUT` | `/api/albums/{album_id}`<br><small>Update Album</small> | Có | path `album_id`*: integer; body application/json: `AlbumCreate` | `200` |
| `POST` | `/api/albums/{album_id}/media`<br><small>Upload Album Media</small> | Có | path `album_id`*: integer; body multipart/form-data: `Body_upload_album_media_api_albums__album_id__media_post` | `200` |
| `DELETE` | `/api/albums/{album_id}/media/{media_id}`<br><small>Delete Album Media</small> | Có | path `album_id`*: integer; path `media_id`*: integer | `200` |

## Auth

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `POST` | `/api/auth/2fa/confirm`<br><small>Confirm Two Factor</small> | Có | body application/json: `TwoFactorConfirm` | `200` |
| `POST` | `/api/auth/2fa/disable`<br><small>Disable Two Factor</small> | Có | body application/json: `PasswordConfirm` | `200` |
| `POST` | `/api/auth/2fa/setup`<br><small>Setup Two Factor</small> | Có | body application/json: `PasswordConfirm` | `200` |
| `POST` | `/api/auth/email/resend`<br><small>Resend Verification</small> | Có | — | `200` |
| `POST` | `/api/auth/email/verify`<br><small>Verify Email</small> | Không | body application/json: `TokenConfirm` | `200` |
| `POST` | `/api/auth/forgot-password`<br><small>Forgot Password</small> | Không | body application/json: `PasswordResetRequest` | `200` |
| `POST` | `/api/auth/login`<br><small>Login</small> | Không | body application/json: `LoginIn` | `200` |
| `POST` | `/api/auth/login/2fa`<br><small>Login Two Factor</small> | Không | body application/json: `TwoFactorLoginIn` | `200` |
| `POST` | `/api/auth/logout`<br><small>Logout</small> | Có | — | `200` |
| `POST` | `/api/auth/logout-all`<br><small>Logout All</small> | Có | — | `200` |
| `POST` | `/api/auth/refresh`<br><small>Refresh</small> | Không | cookie `socialn_refresh`: string | `200` |
| `POST` | `/api/auth/register`<br><small>Register</small> | Không | body application/json: `RegisterIn` | `200` |
| `POST` | `/api/auth/reset-password`<br><small>Reset Password</small> | Không | body application/json: `PasswordResetConfirm` | `200` |
| `GET` | `/api/auth/sessions`<br><small>Sessions</small> | Có | — | `200` |
| `DELETE` | `/api/auth/sessions/{public_id}`<br><small>Revoke Session</small> | Có | path `public_id`*: string | `200` |

## Chat

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/api/chat/conversations`<br><small>Conversations</small> | Có | — | `200` |
| `DELETE` | `/api/chat/conversations/{conversation_id}`<br><small>Clear Conversation</small> | Có | path `conversation_id`*: integer | `200` |
| `POST` | `/api/chat/conversations/{conversation_id}/archive`<br><small>Toggle Archive</small> | Có | path `conversation_id`*: integer | `200` |
| `GET` | `/api/chat/conversations/{conversation_id}/draft`<br><small>Get Draft</small> | Có | path `conversation_id`*: integer | `200` |
| `PUT` | `/api/chat/conversations/{conversation_id}/draft`<br><small>Save Draft</small> | Có | path `conversation_id`*: integer; body application/json: `ConversationDraftIn` | `200` |
| `POST` | `/api/chat/conversations/{conversation_id}/pin`<br><small>Toggle Pin</small> | Có | path `conversation_id`*: integer | `200` |
| `GET` | `/api/chat/conversations/{conversation_id}/search`<br><small>Search Conversation</small> | Có | path `conversation_id`*: integer; query `q`*: string; query `before_id`: integer; query `limit`: integer | `200` |
| `POST` | `/api/chat/group-conversations`<br><small>Create Group Conversation</small> | Có | body application/json: `ChatGroupCreate` | `200` |
| `PUT` | `/api/chat/group-conversations/{group_id}`<br><small>Update Group Conversation</small> | Có | path `group_id`*: integer; body application/json: `ChatGroupUpdate` | `200` |
| `POST` | `/api/chat/group-conversations/{group_id}/join-requests/{request_id}/{action}`<br><small>Review Group Chat Request</small> | Có | path `group_id`*: integer; path `request_id`*: integer; path `action`*: string | `200` |
| `DELETE` | `/api/chat/group-conversations/{group_id}/members/{member_id}`<br><small>Remove Group Chat Member</small> | Có | path `group_id`*: integer; path `member_id`*: integer | `200` |
| `POST` | `/api/chat/group-conversations/{group_id}/members/{member_id}`<br><small>Add Group Chat Member</small> | Có | path `group_id`*: integer; path `member_id`*: integer | `200` |
| `PUT` | `/api/chat/group-conversations/{group_id}/members/{member_id}/nickname`<br><small>Update Group Nickname</small> | Có | path `group_id`*: integer; path `member_id`*: integer; query `nickname`: string | `200` |
| `PUT` | `/api/chat/group-conversations/{group_id}/members/{member_id}/role`<br><small>Set Group Chat Role</small> | Có | path `group_id`*: integer; path `member_id`*: integer; query `role`*: string | `200` |
| `GET` | `/api/chat/group-conversations/{group_id}/messages`<br><small>Group Messages</small> | Có | path `group_id`*: integer | `200` |
| `POST` | `/api/chat/group-conversations/{group_id}/messages`<br><small>Send Group Message</small> | Có | path `group_id`*: integer; body application/json: `MessageCreate` | `200` |
| `POST` | `/api/chat/group-conversations/{group_id}/polls`<br><small>Create Group Poll</small> | Có | path `group_id`*: integer; body application/json: `ChatPollCreate` | `200` |
| `PUT` | `/api/chat/group-conversations/{group_id}/preferences`<br><small>Update Group Preferences</small> | Có | path `group_id`*: integer; query `mute_minutes`: integer; query `sound`: string | `200` |
| `POST` | `/api/chat/group-invites/{token}`<br><small>Join Group Chat By Link</small> | Có | path `token`*: string | `200` |
| `GET` | `/api/chat/message-requests`<br><small>Message Requests</small> | Có | query `folder`: string | `200` |
| `DELETE` | `/api/chat/message-requests/{conversation_id}`<br><small>Delete Message Request</small> | Có | path `conversation_id`*: integer | `204` |
| `POST` | `/api/chat/message-requests/{conversation_id}/accept`<br><small>Accept Message Request</small> | Có | path `conversation_id`*: integer | `200` |
| `POST` | `/api/chat/message-requests/{conversation_id}/restore`<br><small>Restore Message Request</small> | Có | path `conversation_id`*: integer | `200` |
| `POST` | `/api/chat/message-requests/{conversation_id}/spam`<br><small>Spam Message Request</small> | Có | path `conversation_id`*: integer | `200` |
| `DELETE` | `/api/chat/messages/{message_id}`<br><small>Unsend Message</small> | Có | path `message_id`*: integer | `200` |
| `PATCH` | `/api/chat/messages/{message_id}`<br><small>Edit Message</small> | Có | path `message_id`*: integer; body application/json: `MessageEditIn` | `200` |
| `POST` | `/api/chat/messages/{message_id}/forward/{recipient_id}`<br><small>Forward Message</small> | Có | path `message_id`*: integer; path `recipient_id`*: integer | `200` |
| `POST` | `/api/chat/messages/{message_id}/pin`<br><small>Toggle Message Pin</small> | Có | path `message_id`*: integer | `200` |
| `POST` | `/api/chat/messages/{message_id}/reaction`<br><small>React To Message</small> | Có | path `message_id`*: integer; body application/json: `ReactionIn` | `200` |
| `POST` | `/api/chat/messages/{message_id}/view-once`<br><small>Open View Once</small> | Có | path `message_id`*: integer | `200` |
| `POST` | `/api/chat/polls/{poll_id}/vote/{option_id}`<br><small>Vote Group Poll</small> | Có | path `poll_id`*: integer; path `option_id`*: integer | `200` |
| `GET` | `/api/chat/presence/{other_user_id}`<br><small>User Presence</small> | Có | path `other_user_id`*: integer | `200` |
| `GET` | `/api/chat/restricted`<br><small>Restricted Conversations</small> | Có | — | `200` |
| `DELETE` | `/api/chat/restricted/{other_user_id}`<br><small>Unrestrict Conversation</small> | Có | path `other_user_id`*: integer | `200` |
| `GET` | `/api/chat/unread-count`<br><small>Unread Message Count</small> | Có | — | `200` |
| `POST` | `/api/chat/upload`<br><small>Upload Chat File</small> | Có | body multipart/form-data: `Body_upload_chat_file_api_chat_upload_post` | `200` |
| `GET` | `/api/chat/{other_user_id}/messages`<br><small>Messages</small> | Có | path `other_user_id`*: integer; query `before_id`: integer; query `limit`: integer | `200` |
| `POST` | `/api/chat/{other_user_id}/messages`<br><small>Send Message</small> | Có | path `other_user_id`*: integer; body application/json: `MessageCreate` | `200` |
| `GET` | `/api/chat/{other_user_id}/settings`<br><small>Get Direct Settings</small> | Có | path `other_user_id`*: integer | `200` |
| `PUT` | `/api/chat/{other_user_id}/settings`<br><small>Update Direct Settings</small> | Có | path `other_user_id`*: integer; body application/json: `DirectChatUpdate` | `200` |

## Discovery products

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/api/events`<br><small>Events</small> | Có | — | `200` |
| `POST` | `/api/events`<br><small>Create Event</small> | Có | body application/json: `EventCreate` | `201` |
| `PUT` | `/api/events/{event_id}/response`<br><small>Respond Event</small> | Có | path `event_id`*: integer; body application/json: `EventResponseIn` | `200` |
| `GET` | `/api/marketplace`<br><small>Marketplace</small> | Có | query `q`: string | `200` |
| `POST` | `/api/marketplace`<br><small>Create Listing</small> | Có | body application/json: `MarketplaceCreate` | `201` |
| `PATCH` | `/api/marketplace/{listing_id}/status`<br><small>Listing Status</small> | Có | path `listing_id`*: integer; query `status`*: string | `200` |
| `GET` | `/api/pages`<br><small>Pages</small> | Có | query `q`: string | `200` |
| `POST` | `/api/pages`<br><small>Create Page</small> | Có | body application/json: `PageCreate` | `201` |
| `POST` | `/api/pages/{page_id}/follow`<br><small>Follow Page</small> | Có | path `page_id`*: integer | `200` |
| `GET` | `/api/reels`<br><small>Reels</small> | Có | query `cursor`: integer; query `limit`: integer | `200` |
| `POST` | `/api/reels`<br><small>Create Reel</small> | Có | body application/json: `ReelCreate` | `201` |
| `POST` | `/api/reels/{reel_id}/view`<br><small>View Reel</small> | Có | path `reel_id`*: integer | `200` |
| `GET` | `/api/stories`<br><small>Stories</small> | Có | — | `200` |
| `POST` | `/api/stories`<br><small>Create Story</small> | Có | body application/json: `StoryCreate` | `201` |
| `DELETE` | `/api/stories/{story_id}`<br><small>Delete Story</small> | Có | path `story_id`*: integer | `204` |
| `POST` | `/api/stories/{story_id}/view`<br><small>View Story</small> | Có | path `story_id`*: integer | `200` |

## Friends

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/api/friends`<br><small>Friends</small> | Có | — | `200` |
| `GET` | `/api/friends/requests`<br><small>Requests</small> | Có | — | `200` |
| `GET` | `/api/friends/requests/sent`<br><small>Sent Requests</small> | Có | — | `200` |
| `DELETE` | `/api/friends/requests/{request_id}`<br><small>Cancel Sent Request</small> | Có | path `request_id`*: integer | `200` |
| `POST` | `/api/friends/{request_id}/accept`<br><small>Accept Request</small> | Có | path `request_id`*: integer | `200` |
| `POST` | `/api/friends/{request_id}/reject`<br><small>Reject Request</small> | Có | path `request_id`*: integer | `200` |
| `DELETE` | `/api/friends/{target_id}`<br><small>Unfriend</small> | Có | path `target_id`*: integer | `200` |
| `POST` | `/api/friends/{target_id}`<br><small>Send Request</small> | Có | path `target_id`*: integer | `200` |

## GIPHY

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/api/giphy`<br><small>Find Gifs</small> | Có | query `q`: string | `200` |

## Groups

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/api/groups`<br><small>List Groups</small> | Có | query `q`: string | `200` |
| `POST` | `/api/groups`<br><small>Create Group</small> | Có | body application/json: `GroupCreate` | `200` |
| `GET` | `/api/groups/{group_id}`<br><small>Get Group</small> | Có | path `group_id`*: integer | `200` |
| `PUT` | `/api/groups/{group_id}`<br><small>Update Group</small> | Có | path `group_id`*: integer; body application/json: `GroupUpdate` | `200` |
| `PUT` | `/api/groups/{group_id}/cover`<br><small>Update Group Cover</small> | Có | path `group_id`*: integer; body application/json: `GroupCoverUpdate` | `200` |
| `POST` | `/api/groups/{group_id}/join`<br><small>Join Group</small> | Có | path `group_id`*: integer; body application/json: `GroupJoinIn` | `200` |
| `DELETE` | `/api/groups/{group_id}/members/{member_id}`<br><small>Remove Member</small> | Có | path `group_id`*: integer; path `member_id`*: integer; query `ban`: boolean | `200` |
| `POST` | `/api/groups/{group_id}/members/{member_id}`<br><small>Add Member</small> | Có | path `group_id`*: integer; path `member_id`*: integer | `200` |
| `POST` | `/api/groups/{group_id}/members/{member_id}/mute`<br><small>Mute Member</small> | Có | path `group_id`*: integer; path `member_id`*: integer; query `hours`: integer | `200` |
| `PUT` | `/api/groups/{group_id}/members/{member_id}/role`<br><small>Change Role</small> | Có | path `group_id`*: integer; path `member_id`*: integer; query `role`*: string | `200` |
| `DELETE` | `/api/groups/{group_id}/membership`<br><small>Leave Group</small> | Có | path `group_id`*: integer | `200` |
| `POST` | `/api/groups/{group_id}/notifications`<br><small>Toggle Group Notifications</small> | Có | path `group_id`*: integer; query `enabled`*: boolean | `200` |
| `GET` | `/api/groups/{group_id}/posts`<br><small>List Posts</small> | Có | path `group_id`*: integer | `200` |
| `POST` | `/api/groups/{group_id}/posts`<br><small>Create Post</small> | Có | path `group_id`*: integer; body application/json: `GroupPostCreate` | `200` |
| `DELETE` | `/api/groups/{group_id}/posts/{post_id}`<br><small>Delete Post</small> | Có | path `group_id`*: integer; path `post_id`*: integer | `200` |
| `POST` | `/api/groups/{group_id}/posts/{post_id}/comments`<br><small>Comment On Post</small> | Có | path `group_id`*: integer; path `post_id`*: integer; body application/json: `GroupCommentCreate` | `200` |
| `POST` | `/api/groups/{group_id}/posts/{post_id}/hide`<br><small>Hide Post</small> | Có | path `group_id`*: integer; path `post_id`*: integer | `200` |
| `POST` | `/api/groups/{group_id}/posts/{post_id}/moderate/{action}`<br><small>Moderate Post</small> | Có | path `group_id`*: integer; path `post_id`*: integer; path `action`*: string | `200` |
| `POST` | `/api/groups/{group_id}/posts/{post_id}/pin`<br><small>Pin Post</small> | Có | path `group_id`*: integer; path `post_id`*: integer | `200` |
| `POST` | `/api/groups/{group_id}/posts/{post_id}/react`<br><small>React To Post</small> | Có | path `group_id`*: integer; path `post_id`*: integer; body application/json: `ReactionIn` | `200` |
| `POST` | `/api/groups/{group_id}/posts/{post_id}/report`<br><small>Report Post</small> | Có | path `group_id`*: integer; path `post_id`*: integer; body application/json: `GroupReportCreate` | `200` |
| `POST` | `/api/groups/{group_id}/posts/{post_id}/share`<br><small>Share Group Post</small> | Có | path `group_id`*: integer; path `post_id`*: integer | `200` |
| `POST` | `/api/groups/{group_id}/reports/{report_id}/resolve`<br><small>Resolve Report</small> | Có | path `group_id`*: integer; path `report_id`*: integer | `200` |
| `POST` | `/api/groups/{group_id}/requests/{request_id}/{action}`<br><small>Review Request</small> | Có | path `group_id`*: integer; path `request_id`*: integer; path `action`*: string | `200` |

## Notifications

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/api/notifications`<br><small>List Notifications</small> | Có | query `limit`: integer | `200` |
| `PUT` | `/api/notifications/preferences`<br><small>Update Notification Preference</small> | Có | body application/json: `NotificationPreferenceIn` | `200` |
| `GET` | `/api/notifications/preferences/all`<br><small>Notification Preferences</small> | Có | — | `200` |
| `GET` | `/api/notifications/push/public-key`<br><small>Push Public Key</small> | Không | — | `200` |
| `DELETE` | `/api/notifications/push/subscriptions`<br><small>Unsubscribe Push</small> | Có | query `endpoint`*: string | `204` |
| `POST` | `/api/notifications/push/subscriptions`<br><small>Subscribe Push</small> | Có | header `user-agent`: string; body application/json: `PushSubscriptionIn` | `201` |
| `POST` | `/api/notifications/read-all`<br><small>Read All</small> | Có | — | `200` |
| `GET` | `/api/notifications/unread-count`<br><small>Unread Count</small> | Có | — | `200` |
| `POST` | `/api/notifications/{notification_id}/read`<br><small>Read One</small> | Có | path `notification_id`*: integer | `200` |

## Other

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/health`<br><small>Health</small> | Không | — | `200` |

## Posts

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/api/posts`<br><small>Feed</small> | Có | — | `200` |
| `POST` | `/api/posts`<br><small>Create Post</small> | Có | body application/json: `PostCreate` | `200` |
| `PUT` | `/api/posts/authors/{author_id}/preference`<br><small>Set Author Preference</small> | Có | path `author_id`*: integer; body application/json: `FeedAuthorPreferenceIn` | `200` |
| `GET` | `/api/posts/collections`<br><small>Collections</small> | Có | — | `200` |
| `POST` | `/api/posts/collections`<br><small>Create Collection</small> | Có | body application/json: `SavedCollectionIn` | `200` |
| `GET` | `/api/posts/collections/{collection_id}`<br><small>Collection Posts</small> | Có | path `collection_id`*: integer | `200` |
| `GET` | `/api/posts/feed`<br><small>Smart Feed</small> | Có | query `cursor`: string; query `limit`: integer | `200` |
| `GET` | `/api/posts/user/{user_id}`<br><small>User Posts</small> | Có | path `user_id`*: integer | `200` |
| `DELETE` | `/api/posts/{post_id}`<br><small>Delete Post</small> | Có | path `post_id`*: integer | `200` |
| `GET` | `/api/posts/{post_id}`<br><small>Get Post</small> | Có | path `post_id`*: integer | `200` |
| `PUT` | `/api/posts/{post_id}`<br><small>Update Post</small> | Có | path `post_id`*: integer; body application/json: `PostCreate` | `200` |
| `POST` | `/api/posts/{post_id}/comments`<br><small>Comment</small> | Có | path `post_id`*: integer; body application/json: `CommentCreate` | `200` |
| `DELETE` | `/api/posts/{post_id}/comments/{comment_id}`<br><small>Delete Comment</small> | Có | path `post_id`*: integer; path `comment_id`*: integer | `200` |
| `POST` | `/api/posts/{post_id}/hide`<br><small>Hide Post</small> | Có | path `post_id`*: integer | `200` |
| `POST` | `/api/posts/{post_id}/like`<br><small>Toggle Like</small> | Có | path `post_id`*: integer; body application/json: `ReactionIn` | `200` |
| `GET` | `/api/posts/{post_id}/reactions`<br><small>Post Reactions</small> | Có | path `post_id`*: integer | `200` |
| `DELETE` | `/api/posts/{post_id}/save`<br><small>Unsave Post</small> | Có | path `post_id`*: integer; query `collection_id`: integer | `200` |
| `POST` | `/api/posts/{post_id}/save`<br><small>Save Post</small> | Có | path `post_id`*: integer; body application/json: `SavePostIn` | `200` |
| `POST` | `/api/posts/{post_id}/share`<br><small>Share</small> | Có | path `post_id`*: integer; body application/json: `PostShareIn` | `200` |
| `POST` | `/api/posts/{post_id}/show-fewer`<br><small>Show Fewer</small> | Có | path `post_id`*: integer | `200` |

## Search

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/api/search`<br><small>Global Search</small> | Có | query `q`*: string; query `types`: string; query `limit`: integer | `200` |

## Upload

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `POST` | `/api/upload`<br><small>Upload</small> | Có | body multipart/form-data: `Body_upload_api_upload_post` | `200` |

## Users

| Method | Endpoint | Auth | Input | Success |
|---|---|:---:|---|---|
| `GET` | `/api/users/me`<br><small>Me</small> | Có | — | `200` |
| `PUT` | `/api/users/me`<br><small>Update Me</small> | Có | body application/json: `ProfileUpdate` | `200` |
| `PUT` | `/api/users/me/active-status`<br><small>Update Active Status</small> | Có | body application/json: `ActiveStatusUpdate` | `200` |
| `DELETE` | `/api/users/me/avatar`<br><small>Delete Avatar</small> | Có | — | `200` |
| `POST` | `/api/users/me/avatar`<br><small>Avatar</small> | Có | body multipart/form-data: `Body_avatar_api_users_me_avatar_post` | `200` |
| `GET` | `/api/users/me/blocked`<br><small>Blocked Users</small> | Có | — | `200` |
| `DELETE` | `/api/users/me/cover`<br><small>Delete Cover</small> | Có | — | `200` |
| `POST` | `/api/users/me/cover`<br><small>Cover</small> | Có | body multipart/form-data: `Body_cover_api_users_me_cover_post` | `200` |
| `PUT` | `/api/users/me/password`<br><small>Change Password</small> | Có | body application/json: `PasswordChange` | `200` |
| `GET` | `/api/users/me/privacy-settings`<br><small>Get Privacy Settings</small> | Có | — | `200` |
| `PUT` | `/api/users/me/privacy-settings`<br><small>Update Privacy Settings</small> | Có | body application/json: `PrivacySettingsUpdate` | `200` |
| `GET` | `/api/users/me/privacy/checkup`<br><small>Privacy Checkup</small> | Có | — | `200` |
| `POST` | `/api/users/me/privacy/limit-old-posts`<br><small>Limit Old Posts</small> | Có | — | `200` |
| `PUT` | `/api/users/me/username`<br><small>Change Username</small> | Có | body application/json: `UsernameChange` | `200` |
| `GET` | `/api/users/me/username-status`<br><small>Get Username Change Status</small> | Có | — | `200` |
| `POST` | `/api/users/relationship-requests/{request_id}/accept`<br><small>Accept Relationship Request</small> | Có | path `request_id`*: integer | `200` |
| `POST` | `/api/users/relationship-requests/{request_id}/decline`<br><small>Decline Relationship Request</small> | Có | path `request_id`*: integer | `200` |
| `GET` | `/api/users/search`<br><small>Search</small> | Có | query `q`*: string | `200` |
| `GET` | `/api/users/suggestions/people`<br><small>People You May Know</small> | Có | query `limit`: integer | `200` |
| `GET` | `/api/users/username/{username}/profile`<br><small>Profile By Username</small> | Có | path `username`*: string | `200` |
| `DELETE` | `/api/users/{target_id}/block`<br><small>Unblock User</small> | Có | path `target_id`*: integer | `200` |
| `POST` | `/api/users/{target_id}/block`<br><small>Block User</small> | Có | path `target_id`*: integer | `200` |
| `DELETE` | `/api/users/{user_id}/follow`<br><small>Unfollow User</small> | Có | path `user_id`*: integer | `200` |
| `POST` | `/api/users/{user_id}/follow`<br><small>Follow User</small> | Có | path `user_id`*: integer | `200` |
| `GET` | `/api/users/{user_id}/friends`<br><small>Visible Friend List</small> | Có | path `user_id`*: integer | `200` |
| `GET` | `/api/users/{user_id}/profile`<br><small>Public Profile</small> | Có | path `user_id`*: integer | `200` |

