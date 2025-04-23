# Accessing, Searching, and Tailing Logs in S3

This guide explains how to retrieve, search, and tail logs stored in S3/MinIO using logflow, the AWS CLI, and common tools. It is intended for users who need to access logs after they have been forwarded and batched to S3 by logflow.

---

## 1. Understanding Log Storage in S3
- **Format:** Logs are batched and uploaded in JSON Lines (JSONL) format.
- **Naming:** Each batch is stored as a uniquely named object (file) in the configured bucket/prefix.
- **Structure:** Typical S3 path: `s3://<bucket>/<prefix>/<date>/<batch_id>.jsonl`

---

## 2. Listing Log Files in S3
Use the AWS CLI or compatible tools to list log files:

```sh
aws s3 ls s3://<bucket>/<prefix>/ --recursive
```

---

## 3. Downloading Log Files
To fetch a specific log batch:

```sh
aws s3 cp s3://<bucket>/<prefix>/<date>/<batch_id>.jsonl ./
```

---

## 4. Searching Logs in S3
### Option 1: Download and Search Locally
1. Download the relevant log files (see above).
2. Use `jq`, `grep`, or similar tools to search:

```sh
grep "<search-term>" <batch_id>.jsonl
# or
jq 'select(.message | test("<search-term>"))' <batch_id>.jsonl
```

### Option 2: Search In-Place with AWS CLI (S3 Select)
For simple queries on individual files:

```sh
aws s3api select-object-content \
  --bucket <bucket> \
  --key <prefix>/<date>/<batch_id>.jsonl \
  --expression "SELECT * FROM S3Object s WHERE s.message LIKE '%<search-term>%'" \
  --expression-type SQL \
  --input-serialization '{"JSON": {"Type": "LINES"}}' \
  --output-serialization '{"JSON": {}}' <output-options>
```

---

## 5. Tailing Logs from S3
### Option 1: Periodic Polling
Since S3 is not a real-time service, tailing means periodically fetching the latest files:

```sh
while true; do
  aws s3 ls s3://<bucket>/<prefix>/ --recursive | sort | tail -n 5
  sleep 10
  # Optionally download and view new files
  # aws s3 cp ...
done
```

### Option 2: Use MinIO Client (`mc`) for S3-Compatible Endpoints

```sh
mc ls myminio/<bucket>/<prefix>
mc cp myminio/<bucket>/<prefix>/<batch_id>.jsonl ./
```

---

## 6. Best Practices
- Use lifecycle policies to manage retention and cost.
- Use prefixes (e.g., by date/service) for efficient organization.
- Consider Athena or other analytics tools for complex queries.

---

## 7. Future Enhancements
- Planned: Native logflow CLI commands for searching and tailing S3 logs.
- Integration with monitoring tools for alerting on new log batches.

---

## Example: Search for Errors in All Logs (Local)
```sh
aws s3 sync s3://<bucket>/<prefix>/ ./logs/
grep 'ERROR' ./logs/*.jsonl
```

---

For more advanced use cases, see the AWS S3, MinIO, or analytics tool documentation.
