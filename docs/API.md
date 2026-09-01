# SocialN API Documentation

Tài liệu này mô tả API backend SocialN phiên bản **2.0.0**, cách xác thực, quy ước request/response và cách kiểm thử bằng Postman. Nội dung được đối chiếu với OpenAPI sinh bởi ứng dụng ngày **01/09/2026**.

## 1. Mục lục tài liệu

- [Danh mục đầy đủ 175 REST operations](api/endpoints.md)
- [Data dictionary của 58 request schemas](api/schemas.md)
- [Hướng dẫn kiểm thử bằng Postman](api/postman.md)
- [WebSocket và realtime](api/websockets.md)
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Postman collection: [`../postman/SocialN.postman_collection.json`](../postman/SocialN.postman_collection.json)

## 2. Khởi động môi trường

Từ thư mục `socialn`:

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health
```

| Thành phần | Địa chỉ |
|---|---|
| REST API | `http://localhost:8000` |
| Frontend | `http://localhost:5173` |
| Swagger | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| Metrics | `http://localhost:8000/metrics` |
| WebSocket chat | `ws://localhost:8000/api/chat/ws` |
| WebSocket notification | `ws://localhost:8000/api/notifications/ws` |

Health check thành công trả về dạng:

```json
{
  "status": "ok",
  "service": "SocialN API",
  "version": "2.0.0",
  "dependencies": {"database": "configured", "redis": "ok"}
}
```

## 3. Quy ước chung

### 3.1 URL và dữ liệu

- Tất cả nghiệp vụ nằm dưới `/api`, ngoại trừ `/health`, `/metrics` và media `/uploads`.
- Request JSON sử dụng `Content-Type: application/json`.
- Upload sử dụng `multipart/form-data`; không tự đặt `Content-Type` vì client phải sinh boundary.
- Thời gian trả về theo ISO 8601 UTC. Frontend chịu trách nhiệm chuyển sang múi giờ người dùng.
- ID là số nguyên, trừ public session ID và một số invitation/token là chuỗi.
- Endpoint danh sách có thể dùng `limit`, `offset` hoặc `cursor`; xem đúng tham số tại [endpoints.md](api/endpoints.md).

### 3.2 Xác thực

SocialN sử dụng hai lớp token:

1. **Access token JWT ngắn hạn**: gửi trong header `Authorization: Bearer <token>`.
2. **Refresh token xoay vòng**: backend lưu trong cookie HttpOnly `socialn_refresh`, mặc định tồn tại 30 ngày.

Đăng nhập:

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "demo@socialn.local",
  "password": "password123"
}
```

Response thông thường:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900,
  "verification_required": false,
  "requires_2fa": false,
  "user": {
    "id": 1,
    "email": "demo@socialn.local",
    "username": "demo",
    "name": "Demo User"
  }
}
```

Khi tài khoản bật 2FA, `/login` trả `requires_2fa: true` và `challenge_token`. Gửi token đó cùng mã TOTP đến `POST /api/auth/login/2fa`.

Refresh token:

```http
POST /api/auth/refresh
Cookie: socialn_refresh=<HttpOnly cookie>
```

Postman phải bật cookie jar. Không đưa refresh token vào JSON hay biến môi trường.

### 3.3 Quyền truy cập

- `401 Unauthorized`: thiếu access token, token hết hạn hoặc session bị thu hồi.
- `403 Forbidden`: đã xác thực nhưng không có quyền, bị block hoặc không đáp ứng privacy/membership.
- Quyền Admin/Moderator/Member của Group được kiểm tra tại backend, không dựa vào việc ẩn nút frontend.
- Privacy của post/profile/album được áp dụng tại API trước khi serialize dữ liệu.
- Message Request/Restricted không gửi read receipt cho đến khi được chấp nhận theo luồng backend.

### 3.4 Response lỗi

Lỗi nghiệp vụ FastAPI thường có dạng:

```json
{"detail": "Invalid email or password"}
```

Lỗi validation `422`:

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters",
      "input": "123"
    }
  ]
}
```

| Status | Ý nghĩa |
|---:|---|
| `200/201/204` | Thành công; `204` không có response body |
| `400` | Dữ liệu hợp lệ về cấu trúc nhưng sai quy tắc nghiệp vụ |
| `401` | Chưa xác thực hoặc session/token không còn hiệu lực |
| `403` | Không có quyền hoặc bị giới hạn bởi privacy/block/membership |
| `404` | Không tìm thấy tài nguyên hoặc tài nguyên không được phép nhìn thấy |
| `409` | Xung đột trạng thái dữ liệu |
| `410` | Tài nguyên hoặc thời gian khôi phục đã hết hạn |
| `413` | File vượt giới hạn dung lượng |
| `422` | Pydantic validation thất bại |
| `429` | Vượt rate limit |
| `500` | Lỗi nội bộ; dùng request ID/log để điều tra |

## 4. Các module API

| Module | Chức năng chính |
|---|---|
| Auth | Đăng ký, đăng nhập, refresh, logout, email verification, reset password, 2FA, sessions |
| Users | Profile, privacy, relationship, block, follow, active status |
| Friends | Danh sách bạn bè, lời mời đã nhận/đã gửi, accept/reject/cancel/unfriend |
| Posts | Feed, CRUD post, reactions, comments, share, collections, hide/snooze/favorite |
| Albums | Album hệ thống/custom, upload/xóa media và đồng bộ timeline |
| Chat | Chat 1–1, group chat, request/spam/restricted, reaction, reply, pin, forward, settings |
| Notifications | Danh sách, unread, read state, preferences, Web Push subscription |
| Groups | Membership, post, moderation, roles, media/files và cấu hình nhóm |
| Discovery products | Stories, Reels, Pages, Events và Marketplace |
| Account lifecycle | Deactivate, schedule deletion, export và xóa activity history |
| Search | Tìm kiếm hợp nhất theo loại nội dung |
| Upload/GIPHY | Upload media và proxy tìm GIF |

Chi tiết method, path, auth, parameter, body schema và success code của từng endpoint nằm trong [endpoints.md](api/endpoints.md).

## 5. Upload media

Ví dụ upload chung:

```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/photo.jpg"
```

Giới hạn mặc định:

- Image: `100 MB`.
- Video: `2048 MB`.
- File khác: `2048 MB`.
- Search, auth và upload có rate limit riêng.

URL media trả về phải được xem là dữ liệu không tin cậy ở client. Không đưa `GIPHY_API_KEY`, S3 secret hoặc JWT secret vào frontend.

## 6. Phân trang và đồng bộ

- Feed mới dùng cursor: client gửi cursor tiếp theo backend trả về, tránh trùng bài khi dữ liệu thay đổi.
- Một số endpoint quản trị/history vẫn dùng `limit` và `offset`.
- Chat nhận lịch sử qua REST, sau đó nhận message/reaction/typing realtime bằng WebSocket.
- Sau reconnect, client nên gọi lại REST để bù sự kiện có thể bị bỏ lỡ.

## 7. Kiểm thử tự động

```bash
cd backend
pytest

cd ../frontend
npm test
```

Các contract test nên tải `openapi.json`, kiểm tra endpoint quan trọng vẫn tồn tại và xác minh response thực tế phù hợp schema. CI nằm tại `.github/workflows/ci.yml`.

## 8. Cập nhật tài liệu

Khi thêm hoặc sửa route:

1. Khai báo `response_model`, `summary`, `description`, `status_code` và lỗi có thể xảy ra.
2. Cập nhật Pydantic schema thay vì nhận dictionary không định kiểu.
3. Mở `/docs` để thử request.
4. Export lại OpenAPI và cập nhật [endpoints.md](api/endpoints.md), [schemas.md](api/schemas.md).
5. Thêm request quan trọng vào Postman collection và backend test.

Có thể tái sinh hai file reference trực tiếp từ server đang chạy:

```bash
python3 docs/api/generate_reference.py http://localhost:8000/openapi.json
```
