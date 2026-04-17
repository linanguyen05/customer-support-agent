#!/bin/bash
set -e

# Cài đặt các gói cần thiết
apt update -y
apt install -y python3-pip git curl unzip

# Cài AWS CLI v2 (cần thiết để tải từ S3)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Clone code từ GitHub
cd /home/ubuntu
rm -rf customer-support-agent
git clone ${GITHUB_REPO_URL} -b ${GITHUB_BRANCH}
cd customer-support-agent

# Cài Python dependencies
pip3 install -r requirements.txt

# Tạo thư mục local để lưu FAISS index và PDF
mkdir -p /tmp/faiss_data
mkdir -p /home/ubuntu/.aws

# Tải PDF và FAISS index từ S3
aws s3 cp s3://${S3_BUCKET}/data/Company-10k-18pages.pdf /tmp/faiss_data/Company-10k-18pages.pdf
aws s3 cp s3://${S3_BUCKET}/data/faiss.faiss /tmp/faiss_data/faiss.faiss
aws s3 cp s3://${S3_BUCKET}/data/faiss.pkl /tmp/faiss_data/faiss.pkl

# Tạo file .env cho biến môi trường
cat > /home/ubuntu/customer-support-agent/.env <<EOF
S3_BUCKET=${S3_BUCKET}
S3_PDF_KEY=data/Company-10k-18pages.pdf
S3_INDEX_PREFIX=data/
LOCAL_TMP=/tmp/faiss_data
AWS_REGION=${AWS_REGION}
EOF

# Thêm public key cho GitHub Actions (để SSH deploy)
echo "${GITHUB_ACTIONS_PUB_KEY}" >> /home/ubuntu/.ssh/authorized_keys
chmod 600 /home/ubuntu/.ssh/authorized_keys
chown ubuntu:ubuntu /home/ubuntu/.ssh/authorized_keys

# Tạo systemd service cho Streamlit
cat > /etc/systemd/system/streamlit.service <<EOF
[Unit]
Description=Streamlit Customer Support Agent
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/customer-support-agent
EnvironmentFile=/home/ubuntu/customer-support-agent/.env
ExecStart=/usr/local/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable streamlit
systemctl start streamlit

# Auto-shutdown cron: mỗi tiếng kiểm tra nếu không có kết nối HTTP đến cổng 8501 trong 30 phút thì shutdown
cat > /home/ubuntu/auto_shutdown.sh <<'EOF'
#!/bin/bash
# Kiểm tra số kết nối TCP đến cổng 8501 trong 30 phút qua
if ss -tun state established '( dport = 8501 )' | grep -q 'estab'; then
    echo "Active connection found. Not shutting down."
else
    echo "No active connection for 30 minutes. Shutting down..."
    sudo shutdown now
fi
EOF

chmod +x /home/ubuntu/auto_shutdown.sh
(crontab -l 2>/dev/null; echo "0 * * * * /home/ubuntu/auto_shutdown.sh") | crontab -

echo "User data script completed successfully."