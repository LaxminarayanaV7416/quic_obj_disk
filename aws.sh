aws configure set aws_access_key_id test --profile p2p
aws configure set aws_secret_access_key test --profile p2p
aws configure set region us-east-1 --profile p2p


aws --profile p2p --endpoint-url http://localhost:5000 s3 mb s3://my-p2p-bucket

**Upload a File (Standard):**
```bash
echo "Hello P2P" > test.txt
aws --profile p2p --endpoint-url http://localhost:5000 s3 cp project_implimentation_notes.md s3://my-p2p-bucket/project_implimentation_notes.md

**Multipart Upload (Automatic):**
AWS CLI automatically switches to multipart upload if the file is large (default threshold is usually 8MB). You can force it for testing:
```bash
# Create a 20MB file
dd if=/dev/urandom of=largefile.dat bs=1M count=20

# Upload
aws --profile p2p --endpoint-url http://localhost:5001 s3 cp largefile.dat s3://my-p2p-bucket/large.dat

**Download:**
```bash
aws --profile p2p --endpoint-url http://localhost:5001 s3 cp s3://my-p2p-bucket/large.dat ./downloaded.dat

aws --profile p2p --endpoint-url http://localhost:5000 s3 cp s3://my-p2p-bucket/project_implimentation_notes.md ./lax.md

aws --profile p2p --endpoint-url http://localhost:5000 s3 ls
