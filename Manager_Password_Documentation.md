# TÀI LIỆU ĐẶC TẢ KỸ THUẬT VÀ HƯỚNG DẪN VẬN HÀNH: MANAGER PASSWORD
**Phiên bản hệ thống:** 2.0 (Bản sao lưu lưu trữ cục bộ - Corporate Edition)
**Mô hình xác thực:** Hệ thống Xác thực Lai (Hybrid Credentials Setup)

---

## I. TỔNG QUAN HỆ THỐNG ĐỊNH DANH (SYSTEM OVERVIEW)
**Manager Password** là phần mềm quản trị thông tin tình báo số và mật khẩu máy tính để bàn (Desktop Application) hoạt động độc lập (Offline-first). Phần mềm được xây dựng để trở thành một "Két sắt số" tuân thủ các quy tắc mật mã học hiện đại, đảm bảo miễn nhiễm với các trường hợp trộm cắp vật lý thiết bị máy tính của người dùng.

---

## II. ĐẶC TẢ KIẾN TRÚC MẬT MÃ (CRYPTOGRAPHIC ARCHITECTURE)

Hệ thống bảo mật của Manager Password được thiết kế dựa trên ba cơ chế mật mã học cốt lõi nhằm đảm bảo Tính bảo mật (Confidentiality), Tính toàn vẹn (Integrity) và Tính khả dụng (Availability) của dữ liệu.

### 1. Quá trình Dẫn xuất Khóa (Key Derivation Function - KDF)
- **Cơ chế**: Hệ thống sử dụng Hàm Dẫn xuất Khóa dựa trên Mật khẩu **PBKDF2HMAC** (Password-Based Key Derivation Function 2) kết hợp với thuật toán băm (Hash Algorithm) **SHA-256**.
- **Thông số kỹ thuật**: Quá trình dẫn xuất trải qua **100.000 vòng lặp (Iterations)** cùng với một chuỗi hệ số ngẫu nhiên **Salt** (16-bytes). 
- **Đánh giá rủi ro**: Việc thiết lập chi phí vòng lặp khổng lồ sẽ gây ra hiện tượng "nghẽn cổ chai tính toán" (Computational bottleneck) cho mọi máy gia tốc phần cứng hoặc siêu máy tính của tin tặc. Hệ thống chống lại triệt để triết lý tấn công vét cạn (Brute-force) hay dò mật khẩu theo Từ điển.

### 2. Quá trình Mã hóa Khối (Symmetric Block Cipher AEAD)
- **Cơ chế**: Thuật toán Tiên tiến **AES-256** với chế độ hoạt động **GCM** (Galois/Counter Mode).
- **Hệ quy chiếu AEAD**: Ngoài việc mã hóa ra Bản mã (Ciphertext) an toàn, cơ sở dữ liệu `vault_data.json` của hệ thống liên tục được đóng mộc Chữ Ký Điện Tử (Message Authentication Code - MAC). Bất kỳ một sự hiệu chỉnh trái phép dù chỉ là 1 Byte vào cấu trúc tệp cục bộ đều lập tức bị thuật toán phản hồi lỗi từ chối giải mã hòng phòng chống kỹ thuật tiêm mã độc.
- Chế độ sinh chuỗi khởi tạo ngẫu nhiên **IV (Initialization Vector)** ngẫu nhiên khiến hai Mật khẩu giống hệt nhau cũng sinh ra hai dòng Bản mã hoàn toàn đứt gãy, chống phân tích mẫu.

### 3. Phân luồng Xác thực Một Chạm qua Thời gian thực (TOTP Integration)
- Ứng dụng tích hợp cấu trúc **TOTP** (Time-Based One-Time Password) định quy theo chu kỳ mạng lưới UTC toàn cầu. 
- Mọi hoạt động Đăng nhập Phân hệ hằng ngày sẽ đòi hỏi khóa 6 chữ số phát sinh liên tục trong vòng đời 30 giây từ thiết bị uỷ quyền phía xa (Smartphone). 

---

## III. MÔ HÌNH PHÒNG CHỐNG THẤT THOÁT BỘ NHỚ (MEMORY THREAT MODEL)
Một thiết kế hệ thống tối ưu đòi hỏi việc kiểm soát luồng phiên dịch từ lúc Bản mã tĩnh (Data At Rest) biến chuyển thành Bộ nhớ truy cập ngẫu nhiên (Data In Use - RAM).

- **Tối ưu hóa Khung Giao Diện (UI Caching):** Để xử lý hiện tượng "khớp nháy hình ảnh" (Flickering), phân hệ đã mã hóa một cấu trúc con trỏ UI. Khi giải mã tập lệnh, hệ thống chỉ kết nối tham chiếu trực tiếp đến địa chỉ vùng UI (Pointer references), giúp ứng dụng thực thi đóng/mở che giấu mật khẩu (`••••••••`) tức thời mà không phải xây dựng lại cây DOM vật lý.
- **Xóa Vùng Nhớ Bảo Mật (Garbage Collection):** Giao thức đóng vai trò tấm khiên quan trọng nhất của **Manager Password** là tính năng "Đăng Xuất Phiên". Khi phím chức năng này được kích hoạt, hệ thống sẽ thực hiện quá trình WIPE tức thời mọi địa chỉ RAM chứa Chìa Khóa Sinh AES, Bộ đệm Giao Diện và Cấu trúc Mật Khẩu đã giải mã. Quá trình này thiết lập độ rỗng (Nullification) loại bỏ 100% rủi ro từ các mã độc khai thác và Trích lục bộ nhớ máy (Memory Scraping).

---

## IV. TÀI LIỆU HƯỚNG DẪN VẬN HÀNH (OPERATIONAL MANUAL)

### 1. Giai đoạn Khởi tạo (Initial Setup Phase)
**Lưu ý:** Chỉ thực hiện một lần duy nhất tại kỳ bật phần mềm hệ thống đầu tiên. Yêu cầu giờ trên thiết bị đang sử dụng phải khớp UTC quốc tế.
- **Bước định danh 1:** Quản trị viên nhập một Mật Khẩu Chính duy nhất (Master Password). Cung cấp chuẩn xác để hệ thống đúc Khóa AES làm lõi sinh mã.
- **Bước định danh 2:** Khởi động Google Authenticator trên di động. Quét hệ thống mã QR định dạng "Manager_Password_User". Khớp mã 6 chữ số xuống giao diện để hoàn thành kết nối.

### 2. Giai đoạn Lõi Hoạt động (Daily Core Use)
- Ở toàn bộ kỳ vận hành kế tiếp, việc truy cập chỉ đòi hỏi quản trị viên điền đúng mã thông báo (TOTP) theo chu kỳ từ Di động.
- Trình quản trị Kho Bản Mã:
  - Nhập **Tên định danh**, **Email** và nhấn **Thêm Bản Ghi Mới Vào Hệ Thống** để đóng băng dữ liệu xuống cơ sở điện toán.
  - Sử dụng biểu tượng **[Sao Lưu]** nếu muốn sử dụng thuật chuyển bộ nhớ sang khay nhớ dán của Window mà không gây hiện màn hình công khai.
  - Khuyến nghị sử dụng phím **Đăng Xuất Phiên** sau mỗi chu trình làm việc nhằm đóng quy trình nạp nhớ (Purge Memory) theo tiêu chuẩn bảo mật.
