# SocialN WebSocket API

SocialN có hai WebSocket endpoint. WebSocket không xuất hiện trong OpenAPI/Swagger nên được mô tả riêng tại đây.

## Xác thực và kết nối

Access token được truyền qua query parameter:

```text
ws://localhost:8000/api/chat/ws?token=<ACCESS_TOKEN>
ws://localhost:8000/api/notifications/ws?token=<ACCESS_TOKEN>
```

Token thiếu, sai, hết hạn hoặc session bị revoke khiến server đóng kết nối với code `1008`.

Ví dụ JavaScript:

```javascript
const socket = new WebSocket(
  `ws://localhost:8000/api/chat/ws?token=${encodeURIComponent(accessToken)}`
);

socket.addEventListener("open", () => socket.send("ping"));
socket.addEventListener("message", event => {
  const payload = event.data === "pong" ? "pong" : JSON.parse(event.data);
  console.log(payload);
});
```

Không ghi URL chứa token vào log production. Với hệ thống production nên dùng `wss://`.

## Chat WebSocket

Endpoint: `/api/chat/ws`.

- Message mới/reaction được server push sau khi nghiệp vụ REST thành công.
- Client gửi chuỗi `ping`; server trả `pong`.
- Typing 1–1 gửi JSON:

```json
{
  "type": "typing",
  "to_user_id": 2,
  "is_typing": true
}
```

Typing bị chặn nếu target không tồn tại, hai người block nhau hoặc người gửi đang bị target restrict. Event group chat phải được giữ trong channel/group tương ứng, không dùng payload 1–1.

## Notification WebSocket

Endpoint: `/api/notifications/ws`.

- Push thông báo message, friend, reaction, comment và activity cho user đã xác thực.
- Client nên gửi heartbeat text định kỳ. Server dùng heartbeat để kiểm tra session chưa bị revoke và cập nhật presence.
- Khi session bị thu hồi, kết nối bị đóng code `1008`.

## Test bằng Postman

1. New → **WebSocket Request**.
2. Nhập URL với `?token={{token}}`. Nếu Postman không nội suy environment trong URL WebSocket, dán token tạm thời rồi xóa khỏi history sau khi test.
3. Nhấn **Connect**.
4. Gửi `ping`; chat socket phải trả `pong`.
5. Mở account khác, gửi message qua REST và quan sát payload realtime.
6. Với typing, gửi JSON phía trên và quan sát socket của account nhận.
7. Logout/revoke session rồi gửi heartbeat; socket phải bị đóng.

## Reconnect

Client nên reconnect với exponential backoff có giới hạn. Sau reconnect cần:

1. Refresh access token nếu cần.
2. Kết nối WebSocket bằng token mới.
3. Gọi REST để tải lại unread count, notification và lịch sử chat gần nhất.
4. Loại bỏ event trùng theo ID.

