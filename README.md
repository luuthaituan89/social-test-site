# SocialN

> Mạng xã hội full-stack lấy cảm hứng từ những trải nghiệm cốt lõi của Facebook.  
> A full-stack social network inspired by Facebook's core user experience.

[Tiếng Việt](#tiếng-việt) · [English](#english)

---

## Tiếng Việt

### Giới thiệu

SocialN là dự án mạng xã hội full-stack gồm React frontend, FastAPI backend và MySQL. Dự án hỗ trợ hồ sơ cá nhân, bài viết, kết bạn, thông báo, nhắn tin thời gian thực, album ảnh/video và nhiều quy tắc riêng tư.

Đây là một dự án học tập/phát triển độc lập, không phải sản phẩm chính thức và không sử dụng mã nguồn độc quyền của Facebook.

### Tính năng

#### Tài khoản và hồ sơ

- Đăng ký, đăng nhập, đăng xuất bằng JWT.
- Chỉnh sửa tên, ngày sinh, quê quán, giới tính, tình trạng quan hệ và tiểu sử.
- URL hồ sơ theo username, ví dụ `http://localhost:5173/username`.
- Đổi username với thời gian chờ 30 ngày giữa hai lần thay đổi.
- Đổi mật khẩu.
- Tìm kiếm, chặn và bỏ chặn người dùng.
- Thay, căn chỉnh và xóa avatar/ảnh bìa.
- Việc thay avatar hoặc ảnh bìa tạo bài viết trên dòng thời gian và dùng đại từ `his`, `her` hoặc `their` theo giới tính.

#### Bài viết và tương tác

- Tạo, sửa, xóa và chia sẻ bài viết.
- Bài viết văn bản/hình ảnh; video được đưa lên dòng thời gian thông qua album.
- Quyền riêng tư: `public`, `friends`, `only_me`.
- Bình luận bài viết.
- Reaction: Like, Love, Haha, Wow, Sad và Angry.
- Thông báo được cập nhật theo reaction, bình luận, lượt chia sẻ và các hoạt động liên quan.
- Modal xác nhận tùy chỉnh thay cho hộp thoại mặc định của trình duyệt.

#### Bạn bè

- Gửi, chấp nhận hoặc từ chối lời mời kết bạn.
- Hủy kết bạn.
- Xem bạn chung.
- Gợi ý “People You May Know”.
- Quy tắc chặn và quyền riêng tư được kiểm tra tại backend.

#### Tin nhắn thời gian thực

- Gửi và nhận tin nhắn trực tiếp qua REST + WebSocket.
- REST polling dự phòng nếu WebSocket bị gián đoạn.
- Gửi ảnh, video, file và voice message.
- Preview ảnh/video trong ứng dụng và tải file xuống.
- Reaction cho từng tin nhắn.
- Trạng thái Online/Offline, thời gian hoạt động gần nhất và “is typing…”.
- Badge số tin nhắn chưa đọc.
- Ghim, lưu trữ và xóa cuộc trò chuyện khỏi inbox.
- Cho phép tự nhắn tin trong “Personal storage”, luôn được ưu tiên đầu danh sách.

#### Album ảnh/video

- Album hệ thống: Profile pictures, Cover photos và Timeline photos.
- Tạo album tùy chỉnh với tên, mô tả/ghi chú và quyền riêng tư.
- Sửa thông tin hoặc xóa toàn bộ album tùy chỉnh.
- Upload nhiều ảnh/video; tầng ứng dụng không đặt giới hạn số lượng hoặc dung lượng.
- Chọn và xóa media trong album.
- Thêm media vào album sẽ tạo bài viết tương ứng trên timeline.
- Xóa media/album sẽ đồng bộ xóa bài viết và tham chiếu trong Timeline photos.
- Trình preview hỗ trợ cuộn ngang/dọc với media lớn hơn màn hình.

#### Giao diện

- Responsive cho desktop và màn hình nhỏ.
- Light mode và Dark mode trong Settings.
- Theme được lưu trên trình duyệt và giữ nguyên sau khi tải lại trang.
- Error Boundary ngăn lỗi một component làm trắng toàn bộ giao diện.

### Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Frontend | React 19, Vite 7, Lucide React |
| Backend | Python 3.12, FastAPI, Uvicorn |
| ORM | SQLAlchemy 2 |
| Database | MySQL 8.4 |
| Xác thực | JWT, bcrypt |
| Realtime | WebSocket |
| Upload | Multipart + Docker named volume |
| Triển khai local | Docker, Docker Compose |
| Kiểm thử API thủ công | Swagger UI, Postman collection |

### Kiến trúc

```text
Browser
  └── React + Vite (:5173)
        ├── REST/JSON + multipart
        └── WebSocket
               │
               ▼
        FastAPI + Uvicorn (:8000)
               │
               ├── SQLAlchemy ──► MySQL 8.4 (:3306)
               └── /uploads ────► Docker volume uploads_data
```

Các module backend chính:

- `auth`: đăng ký và đăng nhập.
- `users`: hồ sơ, avatar, ảnh bìa, username, mật khẩu, tìm kiếm và chặn.
- `friends`: lời mời, danh sách bạn bè và hủy kết bạn.
- `posts`: bài viết, reaction, bình luận và chia sẻ.
- `chat`: cuộc trò chuyện, tin nhắn, upload, reaction, presence và WebSocket.
- `notifications`: danh sách, trạng thái đã đọc và WebSocket.
- `albums`: album hệ thống/tùy chỉnh và đồng bộ media–timeline.
- `upload`: upload media dùng chung.

### Cấu trúc thư mục

```text
socialn/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── database.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
├── docs/
├── postman/
├── .env.example
├── docker-compose.yml
└── README.md
```

### Chạy bằng Docker — khuyến nghị

Yêu cầu:

- Docker Engine/Desktop.
- Docker Compose v2 (`docker compose`).
- Các cổng `3306`, `8000` và `5173` đang trống.

Các bước:

```bash
git clone <YOUR_REPOSITORY_URL>
cd socialn
cp .env.example .env
```

Mở `.env` và thay mật khẩu cùng `JWT_SECRET` trước khi chạy. Sau đó:

```bash
docker compose up -d --build
```

Truy cập:

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

Xem log và dừng hệ thống:

```bash
docker compose logs -f
docker compose down
```

Dữ liệu MySQL nằm trong volume `mysql_data`; media nằm trong `uploads_data`, vì vậy `docker compose down` không xóa dữ liệu. Lệnh dưới đây **xóa vĩnh viễn cả database và uploads**:

```bash
docker compose down -v
```

### Biến môi trường

| Biến | Ý nghĩa | Ví dụ |
|---|---|---|
| `MYSQL_ROOT_PASSWORD` | Mật khẩu root của MySQL | `change_me_root` |
| `MYSQL_DATABASE` | Tên database | `socialn` |
| `MYSQL_USER` | Tài khoản ứng dụng | `socialn` |
| `MYSQL_PASSWORD` | Mật khẩu tài khoản ứng dụng | `change_me` |
| `DATABASE_URL` | Chuỗi kết nối SQLAlchemy khi chạy local | `mysql+pymysql://...` |
| `JWT_SECRET` | Khóa ký access token | chuỗi ngẫu nhiên dài |
| `JWT_EXPIRE_MINUTES` | Thời hạn token tính bằng phút | `1440` |
| `CORS_ORIGINS` | Frontend được phép gọi API | `http://localhost:5173` |
| `UPLOAD_DIR` | Thư mục upload khi chạy backend thủ công | `./uploads` |
| `VITE_API_URL` | Địa chỉ API dùng khi build/chạy frontend | `http://localhost:8000` |

Không commit `.env`. Repository chỉ nên chứa `.env.example`.

### Chạy thủ công không dùng Docker

Bạn vẫn cần một MySQL đang chạy và một database đã được tạo.

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL='mysql+pymysql://socialn:change_me@127.0.0.1:3306/socialn'
export JWT_SECRET='replace-with-a-long-random-secret'
export CORS_ORIGINS='http://localhost:5173'
export UPLOAD_DIR='./uploads'

uvicorn app.main:app --reload --port 8000
```

Frontend, trong terminal khác:

```bash
cd frontend
npm install
npm run dev
```

### Postman

Import file:

```text
postman/SocialN.postman_collection.json
```

Đặt collection variable `base_url` thành `http://localhost:8000`. Hãy đăng nhập trước; collection sẽ lưu JWT vào biến `token` nếu script của request login được giữ nguyên.

### Lưu ý bảo mật và triển khai production

- Upload album không bị giới hạn ở tầng ứng dụng nhưng vẫn phụ thuộc dung lượng ổ đĩa, timeout, proxy và giới hạn hệ điều hành.
- Dự án hiện tự tạo bảng và bổ sung một số cột khi startup; production nên dùng Alembic migration.
- Nên bổ sung HTTPS, reverse proxy, rate limiting, refresh-token rotation, xác minh email và quản lý session.
- Nên chuyển media sang S3/MinIO, quét virus và kiểm duyệt nội dung.
- Khi scale nhiều backend instance, nên dùng Redis cho presence/pub-sub WebSocket.
- Không sử dụng secret mặc định trong môi trường công khai.

### Xử lý lỗi thường gặp

- **Port đã được sử dụng:** đổi mapping port trong `docker-compose.yml` hoặc dừng service đang chiếm cổng.
- **Backend chưa kết nối MySQL:** chờ healthcheck của database rồi xem `docker compose logs backend db`.
- **Frontend gọi sai API:** kiểm tra `VITE_API_URL` trong service frontend.
- **CORS:** thêm đúng origin frontend vào `CORS_ORIGINS`.
- **Media không hiển thị:** kiểm tra volume `uploads_data`, URL backend và log upload.
- **Thay đổi code chưa xuất hiện:** chạy lại `docker compose up -d --build` và hard refresh trình duyệt.

---

## English

### Overview

SocialN is a full-stack social networking application built with a React frontend, a FastAPI backend, and MySQL. It provides profiles, posts, friendships, notifications, real-time messaging, media albums, and backend-enforced privacy rules.

This is an independent learning/development project. It is not an official Facebook product and does not use Facebook's proprietary source code.

### Features

#### Accounts and profiles

- JWT-based registration, login, and logout.
- Editable name, birth date, hometown, gender, relationship status, and bio.
- Username-based profile URLs such as `http://localhost:5173/username`.
- Username changes with a 30-day cooldown.
- Password changes, user search, blocking, and unblocking.
- Upload, reposition, replace, and remove avatars and cover photos.
- Avatar/cover updates create timeline posts using `his`, `her`, or `their` based on gender.

#### Posts and engagement

- Create, edit, delete, and share posts.
- Text/image posts; videos reach the timeline through album uploads.
- `public`, `friends`, and `only_me` privacy levels.
- Post comments.
- Like, Love, Haha, Wow, Sad, and Angry reactions.
- Notifications for reactions, comments, shares, messages, and friendship activity.
- Styled in-app confirmation dialogs instead of browser-native prompts.

#### Friends

- Send, accept, or reject friend requests and unfriend users.
- Mutual friends and “People You May Know” suggestions.
- Blocking and privacy rules enforced by the backend.

#### Real-time messaging

- Durable REST message delivery plus real-time WebSocket updates.
- REST polling fallback when WebSocket connectivity is interrupted.
- Image, video, file, and voice attachments.
- In-app image/video preview and file downloads.
- Per-message reactions.
- Online/offline presence, last active time, and typing indicators.
- Unread message badges.
- Pin, archive, and remove conversations from the inbox.
- Self-messaging through a Personal storage conversation pinned to the top.

#### Photo and video albums

- System albums for Profile pictures, Cover photos, and Timeline photos.
- Custom albums with a name, description/notes, and privacy setting.
- Edit album details or delete an entire custom album.
- Multi-file image/video upload with no application-level count or size cap.
- Select and delete individual album items.
- Album uploads create corresponding timeline posts.
- Deleting media/albums also removes linked posts and Timeline photo references.
- Scrollable preview for media larger than the current screen.

#### Interface

- Responsive desktop and small-screen layout.
- Light and Dark themes under Settings.
- Theme preference persists in the browser.
- A React Error Boundary prevents a component error from blanking the entire UI.

### Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 7, Lucide React |
| Backend | Python 3.12, FastAPI, Uvicorn |
| ORM | SQLAlchemy 2 |
| Database | MySQL 8.4 |
| Authentication | JWT, bcrypt |
| Real time | WebSocket |
| Uploads | Multipart + Docker named volume |
| Local deployment | Docker, Docker Compose |
| Manual API testing | Swagger UI, Postman collection |

### Architecture

```text
Browser
  └── React + Vite (:5173)
        ├── REST/JSON + multipart
        └── WebSocket
               │
               ▼
        FastAPI + Uvicorn (:8000)
               │
               ├── SQLAlchemy ──► MySQL 8.4 (:3306)
               └── /uploads ────► Docker volume uploads_data
```

Primary backend modules are `auth`, `users`, `friends`, `posts`, `chat`, `notifications`, `albums`, and `upload`.

### Project structure

```text
socialn/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── database.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
├── docs/
├── postman/
├── .env.example
├── docker-compose.yml
└── README.md
```

### Run with Docker — recommended

Requirements:

- Docker Engine/Desktop.
- Docker Compose v2 (`docker compose`).
- Available ports `3306`, `8000`, and `5173`.

Setup and start:

```bash
git clone <YOUR_REPOSITORY_URL>
cd socialn
cp .env.example .env
# Replace passwords and JWT_SECRET in .env before starting.
docker compose up -d --build
```

Open:

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

Logs and shutdown:

```bash
docker compose logs -f
docker compose down
```

MySQL data is stored in `mysql_data`, while user media is stored in `uploads_data`. A normal `docker compose down` keeps both volumes. The following command **permanently deletes the database and uploaded media**:

```bash
docker compose down -v
```

### Environment variables

| Variable | Purpose | Example |
|---|---|---|
| `MYSQL_ROOT_PASSWORD` | MySQL root password | `change_me_root` |
| `MYSQL_DATABASE` | Database name | `socialn` |
| `MYSQL_USER` | Application database user | `socialn` |
| `MYSQL_PASSWORD` | Application database password | `change_me` |
| `DATABASE_URL` | SQLAlchemy URL for a manual/local backend | `mysql+pymysql://...` |
| `JWT_SECRET` | Access-token signing secret | a long random string |
| `JWT_EXPIRE_MINUTES` | Token lifetime in minutes | `1440` |
| `CORS_ORIGINS` | Frontend origins allowed to call the API | `http://localhost:5173` |
| `UPLOAD_DIR` | Upload directory for a manually run backend | `./uploads` |
| `VITE_API_URL` | API address used by the frontend | `http://localhost:8000` |

Never commit `.env`; only `.env.example` should be tracked.

### Run without Docker

A running MySQL instance and an existing database are still required.

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL='mysql+pymysql://socialn:change_me@127.0.0.1:3306/socialn'
export JWT_SECRET='replace-with-a-long-random-secret'
export CORS_ORIGINS='http://localhost:5173'
export UPLOAD_DIR='./uploads'

uvicorn app.main:app --reload --port 8000
```

Frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

### Postman

Import `postman/SocialN.postman_collection.json`, set the `base_url` collection variable to `http://localhost:8000`, and log in first. The login request script stores the JWT in the `token` variable.

### Production and security notes

- Album uploads have no application-level size cap, but disk capacity, timeouts, proxies, browsers, and the operating system still impose practical limits.
- The application currently creates tables and adds selected columns at startup; production deployments should use Alembic migrations.
- Add HTTPS, a reverse proxy, rate limiting, refresh-token rotation, email verification, and session/device management.
- Move uploads to S3/MinIO and add malware scanning and content moderation.
- Use Redis for presence/WebSocket pub-sub when running multiple backend instances.
- Never deploy with the default development secrets.

### Troubleshooting

- **Port already in use:** change the port mapping in `docker-compose.yml` or stop the conflicting service.
- **Backend cannot reach MySQL:** wait for the database healthcheck and inspect `docker compose logs backend db`.
- **Frontend uses the wrong API:** verify `VITE_API_URL` in the frontend service.
- **CORS error:** include the exact frontend origin in `CORS_ORIGINS`.
- **Media does not load:** inspect `uploads_data`, backend URL configuration, and upload logs.
- **Code changes are not visible:** rerun `docker compose up -d --build` and hard-refresh the browser.

---

## License

No license has been selected yet. Add a `LICENSE` file before distributing the project if you want to grant reuse rights.
