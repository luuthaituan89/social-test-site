# Kiểm thử SocialN API bằng Postman

## 1. Chuẩn bị

Khởi động SocialN và kiểm tra:

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

Trong Postman có hai cách import:

### Cách A — Import toàn bộ OpenAPI (khuyến nghị)

1. Chọn **Import**.
2. Chọn **Link**.
3. Nhập `http://localhost:8000/openapi.json`.
4. Chọn **Import as a Postman Collection**.
5. Collection sinh ra chứa toàn bộ REST endpoint hiện có.

### Cách B — Collection smoke test có sẵn

Import file [`../../postman/SocialN.postman_collection.json`](../../postman/SocialN.postman_collection.json). Collection này có sẵn ví dụ đăng ký, đăng nhập, user, friend, post và notification nhưng không thay thế danh mục OpenAPI đầy đủ.

## 2. Tạo Environment

Tạo environment tên `SocialN Local`:

Bạn có thể import trực tiếp [`../../postman/SocialN.local.postman_environment.json`](../../postman/SocialN.local.postman_environment.json), hoặc tạo thủ công theo bảng dưới đây.

| Variable | Initial value | Current value |
|---|---|---|
| `base_url` | `http://localhost:8000` | `http://localhost:8000` |
| `token` | để trống | để trống |
| `user_id` | để trống | để trống |
| `other_user_id` | để trống | để trống |
| `post_id` | để trống | để trống |
| `group_id` | để trống | để trống |
| `conversation_id` | để trống | để trống |

Không lưu password, JWT, refresh cookie hoặc secret thật vào Initial value nếu environment được commit/chia sẻ.

## 3. Cấu hình Authorization

Ở cấp collection:

1. Mở **Authorization**.
2. Type: **Bearer Token**.
3. Token: `{{token}}`.
4. Các request public như register/login chọn **No Auth**.

Header tương đương:

```http
Authorization: Bearer {{token}}
```

## 4. Đăng ký

`POST {{base_url}}/api/auth/register`

Body → raw → JSON:

```json
{
  "email": "demo@socialn.local",
  "username": "demo",
  "name": "Demo User",
  "password": "password123"
}
```

Tests:

```javascript
pm.test("Register succeeded", () => {
  pm.expect(pm.response.code).to.be.oneOf([200, 201]);
});

const data = pm.response.json();
if (data.access_token) pm.collectionVariables.set("token", data.access_token);
if (data.user?.id) pm.collectionVariables.set("user_id", data.user.id);
```

Đăng ký cũng đặt refresh cookie HttpOnly. Mở **Cookies** của `localhost` để xác nhận `socialn_refresh` tồn tại.

## 5. Đăng nhập

`POST {{base_url}}/api/auth/login`

```json
{
  "email": "demo@socialn.local",
  "password": "password123"
}
```

Tests:

```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
const data = pm.response.json();

if (data.requires_2fa) {
  pm.collectionVariables.set("challenge_token", data.challenge_token);
} else {
  pm.expect(data.access_token).to.be.a("string");
  pm.collectionVariables.set("token", data.access_token);
  pm.collectionVariables.set("user_id", data.user.id);
}
```

Nếu có 2FA, gọi `POST /api/auth/login/2fa`:

```json
{
  "challenge_token": "{{challenge_token}}",
  "code": "123456"
}
```

## 6. Refresh session

`POST {{base_url}}/api/auth/refresh` dùng **No Auth** và không cần body. Postman tự gửi cookie `socialn_refresh` từ cookie jar.

Tests:

```javascript
pm.test("Access token refreshed", () => pm.response.to.have.status(200));
const data = pm.response.json();
pm.collectionVariables.set("token", data.access_token);
```

Nếu nhận `401 Refresh session not found`, kiểm tra:

- Login và refresh dùng cùng hostname (`localhost`, không trộn với `127.0.0.1`).
- Cookie jar không bị tắt.
- Request login trước đó nhận header `Set-Cookie`.

## 7. Kiểm tra endpoint có bảo vệ

`GET {{base_url}}/api/users/me`

Tests:

```javascript
pm.test("Authenticated profile returned", () => {
  pm.response.to.have.status(200);
  const data = pm.response.json();
  pm.expect(data.id).to.eql(Number(pm.collectionVariables.get("user_id")));
});
```

Sau đó tạo bản sao request, bỏ Authorization và xác minh:

```javascript
pm.test("Missing token is rejected", () => pm.response.to.have.status(401));
```

## 8. Tạo và tương tác bài viết

Tạo post: `POST {{base_url}}/api/posts`

```json
{
  "content": "Post created from Postman",
  "privacy": "public",
  "image_url": null,
  "media_type": null,
  "sticker": null,
  "audience": {
    "base": "friends",
    "included_ids": [],
    "excluded_ids": []
  }
}
```

Tests:

```javascript
pm.test("Post created", () => pm.expect(pm.response.code).to.be.oneOf([200, 201]));
const data = pm.response.json();
pm.collectionVariables.set("post_id", data.id);
```

Sau đó thử:

- `POST /api/posts/{{post_id}}/like` với reaction hợp lệ.
- `POST /api/posts/{{post_id}}/comments`.
- `POST /api/posts/{{post_id}}/share`.
- `GET /api/posts/{{post_id}}/reactions`.
- `DELETE /api/posts/{{post_id}}` bằng chính tác giả.

## 9. Upload file

Với `POST {{base_url}}/api/upload`:

1. Body → **form-data**.
2. Key: `file`.
3. Đổi loại key từ Text sang **File**.
4. Chọn ảnh/video/tài liệu.
5. Không tự thêm header `Content-Type`; Postman sẽ sinh multipart boundary.

Tests:

```javascript
pm.test("Upload succeeded", () => pm.response.to.have.status(200));
const data = pm.response.json();
pm.expect(data.url).to.be.a("string");
pm.collectionVariables.set("uploaded_url", data.url);
```

Test thêm file vượt giới hạn hoặc MIME không được phép và kỳ vọng `400/413`.

## 10. Test hai tài khoản

Friendship, message, privacy và block cần ít nhất hai account:

1. Tạo hai environment `SocialN User A` và `SocialN User B`, hoặc dùng hai collection variable `token_a`, `token_b`.
2. A gửi friend request đến `other_user_id`.
3. B đọc danh sách request và accept.
4. A tạo post Friends; B phải đọc được.
5. B unfriend/restrict/block; kiểm tra lại feed, profile và chat.

Không dùng cùng một biến `token` cho hai request chạy song song trong Collection Runner.

## 11. Collection Runner

Ở cấp collection thêm test chung:

```javascript
pm.test("Response time is acceptable", () => {
  pm.expect(pm.response.responseTime).to.be.below(2000);
});

pm.test("Response is JSON when it has a body", () => {
  if (pm.response.code !== 204) {
    pm.expect(pm.response.headers.get("Content-Type")).to.include("application/json");
  }
});
```

Chạy collection theo thứ tự: Health → Register/Login → User → Friends → Posts → Chat → Notifications → Logout.

## 12. Negative/security test tối thiểu

| Trường hợp | Kỳ vọng |
|---|---|
| Không có Bearer token | `401` |
| Token bị sửa một ký tự | `401` |
| Password dưới 8 ký tự | `422` |
| User A sửa/xóa tài nguyên của B | `403/404` |
| User bị block gửi tin nhắn | `403` |
| Member gọi endpoint chỉ Admin được dùng | `403` |
| ID không tồn tại | `404` |
| Upload quá giới hạn | `413` |
| Gửi nhanh quá rate limit | `429` |
| Refresh token đã rotate bị tái sử dụng | `401` và session bị từ chối |

## 13. Chạy bằng Newman

Sau khi export collection/environment từ Postman:

```bash
npx newman run SocialN.postman_collection.json \
  -e SocialN-Local.postman_environment.json \
  --reporters cli,junit \
  --reporter-junit-export reports/postman.xml
```

Không commit environment chứa token/password thật.
