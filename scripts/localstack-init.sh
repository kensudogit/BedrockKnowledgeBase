#!/bin/sh
set -e
echo "LocalStack init: creating demo S3 bucket"
awslocal s3 mb s3://bkb-documents-local || true
echo "done"
