# SocialN

> Mạng xã hội full-stack lấy cảm hứng từ các trải nghiệm quen thuộc của Facebook/Messenger.
> A full-stack social network inspired by familiar Facebook and Messenger experiences.

[Tiếng Việt](#tiếng-việt) · [English](#english)

SocialN là dự án học tập/phát triển độc lập, không phải sản phẩm chính thức của Facebook/Meta và không sử dụng mã nguồn độc quyền của họ.

---

## Tiếng Việt

### Tổng quan

SocialN kết hợp React 19 + Vite ở frontend, FastAPI + SQLAlchemy ở backend và MySQL 8.4. Ứng dụng có hồ sơ cá nhân, bảng tin, kết bạn, thông báo, album ảnh/video, chat thời gian thực và tích hợp GIPHY cho GIF.

### Chức năng hiện có

#### Tài khoản và hồ sơ

- Đăng ký, đăng nhập và đăng xuất bằng JWT.
- Hồ sơ theo username, ví dụ `http://localhost:5173/thaituan`.
- Chỉnh sửa tên, tiểu sử, ngày sinh, quê quán, giới tính và tình trạng quan hệ.
- Đổi username; mỗi lần đổi cách nhau ít nhất 30 ngày.
- Đổi mật khẩu, tìm kiếm, chặn và bỏ chặn người dùng.
- Cắt/chọn vùng avatar, kéo vị trí ảnh bìa, thay hoặc xóa ảnh.
- Thay avatar/ảnh bìa tạo bài viết timeline với đại từ `his`, `her` hoặc `their` theo giới tính.

#### Bài viết

- Tạo, sửa, xóa và chia sẻ bài viết.
- Nội dung chữ, ảnh, GIF GIPHY và Sticker/emoji chèn trực tiếp như ký tự tại con trỏ.
- Tìm GIF thịnh hành hoặc theo từ khóa; có preview và nút bỏ lựa chọn.
- Quyền riêng tư: `public`, `friends`, `only_me`.
- Bình luận và reaction: Like, Love, Haha, Wow, Sad, Angry.
- Thông báo cho các hoạt động tương tác liên quan.
- Hộp thoại xác nhận tùy chỉnh thay cho `alert/confirm` mặc định ở các luồng đã hỗ trợ.

#### Bạn bè

- Gửi, chấp nhận, từ chối lời mời; hủy kết bạn.
- Danh sách bạn, bạn chung và People You May Know.
- Backend kiểm tra quan hệ chặn và quyền riêng tư.

#### Messages

- Chat trực tiếp qua REST + WebSocket; polling là phương án dự phòng.
- Tự nhắn tin trong Personal storage, luôn ở đầu danh sách.
- Ghim, lưu trữ và xóa hội thoại khỏi inbox.
- Gửi chữ, Sticker/emoji như ký tự, GIF GIPHY, ảnh, video, file và voice message.
- Giới hạn một file chat ở tầng ứng dụng: **2048 MB (2 GB)**.
- Preview ảnh/video/GIF, tải file, reaction từng tin nhắn.
- Tự cuộn sau khi media tải xong.
- Online/Offline, thời gian hoạt động gần nhất và `is typing...`.
- Badge tin nhắn chưa đọc và badge thông báo.

#### Album ảnh/video

- Album hệ thống: Profile pictures, Cover photos, Timeline photos.
- Tạo album tùy chỉnh với tên, mô tả và quyền riêng tư.
- Sửa/xóa album, upload nhiều ảnh/video, chọn và xóa media.
- Thêm media tạo bài viết timeline; xóa media/album đồng bộ bài viết và Timeline photos liên quan.
- Album hệ thống chỉ nhận media từ đúng luồng avatar, ảnh bìa hoặc timeline.
- Viewer hỗ trợ cuộn khi media lớn hơn màn hình.
- Code không đặt quota tổng cho album; giới hạn thực tế vẫn phụ thuộc ổ đĩa, reverse proxy, timeout và tài nguyên máy chủ.

#### Giao diện và ngôn ngữ

- Responsive desktop/mobile, Light/Dark mode lưu trong trình duyệt.
- Sáu ngôn ngữ: Tiếng Việt, English, 한국어, 日本語, 中文 và ไทย.
- Chọn ngôn ngữ ở trang đăng nhập hoặc trong Settings.
- Error Boundary hiển thị lỗi giao diện thay vì trang trắng.

### Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Frontend | React 19.1, Vite 7.1, Lucide React |
| Backend | Python 3.12, FastAPI 0.116, Uvicorn |
| ORM / DB | SQLAlchemy 2.0, PyMySQL, MySQL 8.4 |
| Auth | JWT (`python-jose`), bcrypt/passlib |
| Realtime | WebSocket + REST polling fallback |
| Media | Multipart upload, Docker volume |
| GIF | GIPHY Search/Trending qua backend proxy |
| Local stack | Docker Compose |

### Kiến trúc

```text
Browser
  └─ React + Vite (:5173)
      ├─ REST/JSON + multipart ──────┐
      └─ WebSocket ──────────────────┤
                                     ▼
                         FastAPI + Uvicorn (:8000)
                            ├─ SQLAlchemy ── MySQL (:3306)
                            ├─ /uploads ──── uploads_data
                            └─ GIPHY proxy ─ GIPHY API
```

Backend được chia thành các route: `auth`, `users`, `friends`, `posts`, `chat`, `notifications`, `albums`, `upload` và `giphy`.

### Cấu trúc dự án

```text
socialn/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   ├── auth.py, config.py, database.py
│   │   ├── main.py, models.py, schemas.py
│   │   └── notifications.py, utils.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/main.jsx
│   ├── src/styles.css
│   ├── src/i18n.js
│   ├── Dockerfile
│   └── package.json
├── docs/architecture.md
├── postman/SocialN.postman_collection.json
├── .env.example
├── docker-compose.yml
└── README.md
```

### Chạy với Docker Compose (khuyến nghị)

Yêu cầu: Docker Engine/Desktop, Compose v2 và các cổng `3306`, `8000`, `5173` đang trống.

```bash
git clone <YOUR_REPOSITORY_URL>
cd socialn
cp .env.example .env
```

Mở `.env`, thay password, `JWT_SECRET` và thêm GIPHY API key nếu dùng GIF:

```env
GIPHY_API_KEY=your_giphy_api_key
```

Không dùng prefix `VITE_` cho key này: SocialN gọi GIPHY qua backend để tránh đưa key vào bundle trình duyệt.

```bash
docker compose up -d --build
```

| Dịch vụ | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |

Các lệnh hữu ích:

```bash
docker compose ps
docker compose logs -f backend frontend
docker compose up -d --build backend frontend
docker compose down
```

`docker compose down` giữ dữ liệu trong `mysql_data` và `uploads_data`. Lệnh sau xóa vĩnh viễn cả database và media:

```bash
docker compose down -v
```

### Biến môi trường

| Biến | Mục đích |
|---|---|
| `MYSQL_ROOT_PASSWORD` | Mật khẩu root MySQL |
| `MYSQL_DATABASE` | Tên database |
| `MYSQL_USER`, `MYSQL_PASSWORD` | Tài khoản ứng dụng |
| `DATABASE_URL` | SQLAlchemy connection URL khi chạy thủ công |
| `JWT_SECRET` | Khóa ký JWT; phải dùng chuỗi ngẫu nhiên dài |
| `JWT_EXPIRE_MINUTES` | Thời hạn access token, mặc định `1440` phút |
| `CORS_ORIGINS` | Danh sách origin frontend, phân cách bằng dấu phẩy |
| `GIPHY_API_KEY` | GIPHY key dùng ở backend |
| `UPLOAD_DIR` | Thư mục upload khi chạy backend ngoài Docker |
| `VITE_API_URL` | Base URL của API mà frontend gọi |

Không commit `.env` hoặc API key. Chỉ commit `.env.example` với giá trị mẫu.

### Chạy thủ công

Cần một MySQL đã chạy và database đã được tạo.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL='mysql+pymysql://socialn:password@127.0.0.1:3306/socialn'
export JWT_SECRET='replace-with-a-long-random-secret'
export CORS_ORIGINS='http://localhost:5173'
export UPLOAD_DIR='./uploads'
export GIPHY_API_KEY='your-giphy-api-key'

uvicorn app.main:app --reload --port 8000
```

Trong terminal khác:

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

### Kiểm thử API

- Swagger: `http://localhost:8000/docs`.
- Import `postman/SocialN.postman_collection.json` và đặt `base_url=http://localhost:8000`.
- Health check: `curl http://localhost:8000/health`.

### Lưu ý production

- Startup hiện gọi `create_all` và bổ sung cột tương thích; production nên dùng Alembic migration.
- Nên dùng HTTPS/reverse proxy, rate limiting, refresh token, xác minh email và quản lý session.
- Nên chuyển media sang object storage, quét virus và kiểm duyệt nội dung.
- File chat 2 GB cần cấu hình đồng bộ giới hạn body/timeout ở proxy và hạ tầng.
- Khi chạy nhiều backend instance, dùng Redis/pub-sub cho WebSocket và presence.
- Giới hạn/ràng buộc sử dụng GIPHY phụ thuộc tài khoản và điều khoản GIPHY của bạn.

### Xử lý lỗi nhanh

- **GIF không tải:** kiểm tra `GIPHY_API_KEY`, rồi recreate backend: `docker compose up -d --force-recreate backend`.
- **Frontend chưa cập nhật:** `docker compose up -d --build frontend`, sau đó hard refresh.
- **Không kết nối database:** xem `docker compose logs db backend` và đợi healthcheck.
- **CORS/API sai:** kiểm tra `CORS_ORIGINS` và `VITE_API_URL`.
- **Media lỗi:** kiểm tra volume `uploads_data`, dung lượng ổ đĩa và log backend.
- **Port bận:** đổi port mapping hoặc dừng service đang sử dụng cổng.

---

## English

### Overview

SocialN combines a React 19 + Vite frontend, a FastAPI + SQLAlchemy backend, and MySQL 8.4. It provides profiles, a social feed, friendships, notifications, photo/video albums, realtime messaging, and GIPHY-powered GIFs.

### Current features

#### Accounts and profiles

- JWT registration, login, and logout.
- Username-based profile URLs such as `http://localhost:5173/thaituan`.
- Edit name, bio, date of birth, hometown, gender, and relationship status.
- Username changes with a 30-day cooldown.
- Password changes, user search, blocking, and unblocking.
- Avatar crop/selection, cover repositioning, replacement, and removal.
- Avatar/cover changes create timeline posts using `his`, `her`, or `their` based on gender.

#### Posts

- Create, edit, delete, and share posts.
- Text, image, GIPHY GIF, and Sticker/emoji content inserted at the caret like normal characters.
- Trending/searchable GIF picker with preview and removal.
- `public`, `friends`, and `only_me` privacy.
- Comments and Like, Love, Haha, Wow, Sad, and Angry reactions.
- Related activity notifications and custom confirmation dialogs in supported flows.

#### Friends

- Send, accept, or reject requests; unfriend users.
- Friend lists, mutual friends, and People You May Know.
- Backend-enforced privacy and blocking rules.

#### Messages

- Direct messaging over REST + WebSocket with polling fallback.
- Self-messaging Personal storage pinned to the top.
- Pin, archive, and remove conversations from the inbox.
- Send text, inline Sticker/emoji characters, GIPHY GIFs, images, videos, files, and voice messages.
- Application-level per-file chat limit: **2048 MB (2 GB)**.
- In-app media preview/download, message reactions, and auto-scroll after media loads.
- Online/Offline, last active time, typing indicator, unread message and notification badges.

#### Photo/video albums

- System albums: Profile pictures, Cover photos, and Timeline photos.
- Custom albums with name, description, and privacy.
- Edit/delete albums; upload, select, and delete multiple media items.
- Album media creates timeline posts; deletion synchronizes related posts and Timeline photos.
- System albums are populated only through their corresponding profile/timeline flows.
- Scrollable large-media viewer.
- No application-level total album quota; practical limits still depend on storage, proxy, timeout, and server resources.

#### UI and languages

- Responsive desktop/mobile UI and persistent Light/Dark themes.
- Vietnamese, English, Korean, Japanese, Chinese, and Thai.
- Language selection on authentication pages and in Settings.
- Error Boundary prevents a component failure from producing a blank page.

### Technology

| Layer | Technology |
|---|---|
| Frontend | React 19.1, Vite 7.1, Lucide React |
| Backend | Python 3.12, FastAPI 0.116, Uvicorn |
| ORM / DB | SQLAlchemy 2.0, PyMySQL, MySQL 8.4 |
| Authentication | JWT, bcrypt/passlib |
| Realtime | WebSocket + REST polling fallback |
| Media | Multipart uploads and Docker volumes |
| GIF | GIPHY Search/Trending through a backend proxy |
| Local stack | Docker Compose |

### Architecture and repository layout

```text
Browser (React/Vite :5173)
  ├─ REST/JSON, multipart
  └─ WebSocket
        ▼
FastAPI/Uvicorn :8000
  ├─ SQLAlchemy → MySQL :3306
  ├─ /uploads → uploads_data
  └─ GIPHY proxy → GIPHY API
```

```text
socialn/
├── backend/app/        # API, models, schemas, route modules
├── frontend/src/       # React entry, styles, translations
├── docs/               # Architecture notes
├── postman/            # API collection
├── .env.example
├── docker-compose.yml
└── README.md
```

Backend route modules are `auth`, `users`, `friends`, `posts`, `chat`, `notifications`, `albums`, `upload`, and `giphy`.

### Run with Docker Compose (recommended)

Requirements: Docker Engine/Desktop, Compose v2, and available ports `3306`, `8000`, and `5173`.

```bash
git clone <YOUR_REPOSITORY_URL>
cd socialn
cp .env.example .env
```

Edit `.env`: replace database passwords and `JWT_SECRET`, then add a GIPHY key to enable GIF search:

```env
GIPHY_API_KEY=your_giphy_api_key
```

The key intentionally has no `VITE_` prefix: GIPHY requests go through the backend so the key is not embedded in browser JavaScript.

```bash
docker compose up -d --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |

Useful commands:

```bash
docker compose ps
docker compose logs -f backend frontend
docker compose up -d --build backend frontend
docker compose down
```

`docker compose down` preserves `mysql_data` and `uploads_data`. The following command permanently deletes both database and uploaded media:

```bash
docker compose down -v
```

### Environment variables

| Variable | Purpose |
|---|---|
| `MYSQL_ROOT_PASSWORD` | MySQL root password |
| `MYSQL_DATABASE` | Database name |
| `MYSQL_USER`, `MYSQL_PASSWORD` | Application database account |
| `DATABASE_URL` | SQLAlchemy connection URL for manual runs |
| `JWT_SECRET` | JWT signing key; use a long random value |
| `JWT_EXPIRE_MINUTES` | Access-token lifetime, default `1440` minutes |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `GIPHY_API_KEY` | Server-side GIPHY API key |
| `UPLOAD_DIR` | Upload directory for non-Docker backend runs |
| `VITE_API_URL` | API base URL used by the frontend |

Never commit `.env` or API keys. Commit only `.env.example` with placeholders.

### Run without Docker

Start MySQL and create the database first.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL='mysql+pymysql://socialn:password@127.0.0.1:3306/socialn'
export JWT_SECRET='replace-with-a-long-random-secret'
export CORS_ORIGINS='http://localhost:5173'
export UPLOAD_DIR='./uploads'
export GIPHY_API_KEY='your-giphy-api-key'

uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

### API testing

- Swagger: `http://localhost:8000/docs`.
- Import `postman/SocialN.postman_collection.json` and set `base_url=http://localhost:8000`.
- Health check: `curl http://localhost:8000/health`.

### Production notes

- Startup currently uses `create_all` and compatibility column additions; use Alembic migrations in production.
- Add HTTPS/reverse proxying, rate limiting, refresh tokens, email verification, and session management.
- Move media to object storage and add malware/content scanning.
- A 2 GB chat upload requires matching body-size and timeout settings across the proxy and infrastructure.
- Use Redis/pub-sub for WebSocket delivery and presence when scaling to multiple backend instances.
- GIPHY usage limits and requirements depend on your GIPHY account and terms.

### Troubleshooting

- **GIFs do not load:** verify `GIPHY_API_KEY`, then run `docker compose up -d --force-recreate backend`.
- **Frontend changes are stale:** rebuild with `docker compose up -d --build frontend`, then hard refresh.
- **Database connection fails:** inspect `docker compose logs db backend` and wait for the healthcheck.
- **CORS/wrong API:** verify `CORS_ORIGINS` and `VITE_API_URL`.
- **Media fails:** inspect `uploads_data`, free disk space, and backend logs.
- **Port conflict:** change Compose port mappings or stop the conflicting service.
