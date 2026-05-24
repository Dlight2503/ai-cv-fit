# S3 Cleanup & Lifecycle Checklist

## Cấu trúc prefix trong bucket

```
{S3_BUCKET}/
├── {S3_PREFIX}/
│   ├── cv/
│   │   └── {job_id}/resume.pdf
│   └── reports/
│       └── {job_id}/report.docx
```

Ví dụ với `S3_PREFIX=dev`:
```
ai-cv-fit-bucket/
└── dev/
    ├── cv/abc-123/resume.pdf
    └── reports/abc-123/report.docx
```

---

## Manual Cleanup (Dev / Demo)

### Xóa tất cả CV cũ hơn N ngày (AWS CLI)

```bash
# Xóa CV cũ hơn 7 ngày trong prefix dev
BUCKET="your-bucket-name"
PREFIX="dev/cv"
CUTOFF=$(date -d "7 days ago" +%Y-%m-%dT%H:%M:%S)

aws s3api list-objects-v2 \
  --bucket "$BUCKET" \
  --prefix "$PREFIX/" \
  --query "Contents[?LastModified<='$CUTOFF'].Key" \
  --output text | tr '\t' '\n' | while read key; do
    echo "Deleting: $key"
    aws s3 rm "s3://$BUCKET/$key"
done
```

### Xóa toàn bộ prefix (NGUY HIỂM — chỉ dùng cho dev)

```bash
# ⚠️ XÓA KHÔNG PHỤC HỒI ĐƯỢC
aws s3 rm s3://your-bucket/dev/ --recursive
```

### List objects theo prefix để kiểm tra

```bash
# Đếm số file CV
aws s3 ls s3://your-bucket/dev/cv/ --recursive | wc -l

# Xem dung lượng
aws s3 ls s3://your-bucket/dev/ --recursive --human-readable --summarize | tail -2
```

---

## S3 Lifecycle Policy

### Gợi ý policy cho môi trường dev/demo

| Prefix | Expire sau | Lý do |
|--------|-----------|-------|
| `dev/cv/` | 7 ngày | CV upload chỉ cần trong quá trình xử lý |
| `dev/reports/` | 30 ngày | Giữ lâu hơn để user tải về |
| `staging/cv/` | 3 ngày | Staging cần clean thường xuyên hơn |
| `staging/reports/` | 14 ngày | |
| `prod/cv/` | 90 ngày | Giữ để debug nếu có vấn đề |
| `prod/reports/` | 1 năm | User có thể cần tải lại |

### Cách set lifecycle rule trên AWS Console

1. Vào **S3 Console** → chọn bucket → tab **Management**
2. Click **Create lifecycle rule**
3. Điền:
   - **Rule name**: `expire-dev-cv`
   - **Prefix**: `dev/cv/`
   - **Lifecycle rule actions**: ✅ Expire current versions of objects
   - **Days after object creation**: `7`
4. Click **Create rule**
5. Lặp lại cho `dev/reports/` với 30 ngày

### Cách set bằng AWS CLI

```bash
# Tạo file lifecycle.json
cat > /tmp/lifecycle.json << 'EOF'
{
  "Rules": [
    {
      "ID": "expire-dev-cv",
      "Filter": { "Prefix": "dev/cv/" },
      "Status": "Enabled",
      "Expiration": { "Days": 7 }
    },
    {
      "ID": "expire-dev-reports",
      "Filter": { "Prefix": "dev/reports/" },
      "Status": "Enabled",
      "Expiration": { "Days": 30 }
    }
  ]
}
EOF

# Apply lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket your-bucket-name \
  --lifecycle-configuration file:///tmp/lifecycle.json

# Kiểm tra policy đã được set
aws s3api get-bucket-lifecycle-configuration --bucket your-bucket-name
```

### Với S3-compatible storage (Cloudflare R2, MinIO, Backblaze B2)

Các provider khác nhau có cách set lifecycle policy khác nhau:

**Cloudflare R2:**
- Vào R2 Dashboard → bucket → Settings → Object Lifecycle
- Add rule: Prefix + số ngày expire

**MinIO (self-hosted):**
```bash
mc ilm add --expiry-days 7 myminio/your-bucket/dev/cv/
mc ilm ls myminio/your-bucket
```

**Backblaze B2:**
- Lifecycle rules đặt ở bucket level, không theo prefix
- Cân nhắc dùng separate bucket cho dev và prod

---

## Checklist trước khi deploy / sau mỗi sprint

```
[ ] Kiểm tra dung lượng bucket hiện tại
[ ] Xác nhận lifecycle rules đã được set đúng prefix
[ ] Xóa manual các test objects cũ nếu lifecycle chưa kick in
[ ] Verify không có CV thật bị upload vào prefix dev/staging
[ ] Kiểm tra object count theo prefix: aws s3 ls --recursive | wc -l
[ ] Đảm bảo prod prefix có versioning bật (phòng xóa nhầm)
```

### Bật versioning cho prod bucket (khuyến nghị)

```bash
aws s3api put-bucket-versioning \
  --bucket your-bucket-name \
  --versioning-configuration Status=Enabled
```

---

## Ghi chú bảo mật

- Không commit `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY` vào Git
- Dùng IAM role với least-privilege: chỉ cần `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` cho prefix cụ thể
- Bật S3 Block Public Access cho toàn bucket — dùng presigned URL để share
- Log S3 access vào CloudTrail hoặc S3 server access logging

### IAM policy tối giản cho app

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::your-bucket/prod/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::your-bucket",
      "Condition": {
        "StringLike": { "s3:prefix": ["prod/*"] }
      }
    }
  ]
}
```
