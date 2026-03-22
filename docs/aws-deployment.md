# AWS Deployment Baseline

This guide turns CarteiraConsol from a cloud-capable codebase into a practical first AWS deployment baseline.

It intentionally keeps the architecture small and production-minded:

- event-driven ingestion runs on Lambda
- the authenticated FastAPI application runs separately
- the frontend is deployed as a static app
- secrets live outside the repository

## Recommended AWS Architecture

```text
Frontend (S3 + CloudFront)
    ↓
FastAPI API (ECS Fargate)
    ↓
RDS PostgreSQL

Raw portfolio files
    ↓
S3
    ↓
S3 event notification
    ↓
SQS
    ↓
Lambda ETL ingestion
    ↓
RDS PostgreSQL + ingestion_reports
```

## Why This Architecture

### Lambda for ingestion

Lambda is the right fit for the ingestion path because the workload is:

- event-driven
- bursty
- naturally triggered by file arrival
- easy to isolate from the user-facing API runtime

Using Lambda for S3-triggered ETL keeps ingestion operationally separate from the authenticated product experience and makes retries easier when paired with SQS.

### SQS between S3 and Lambda

SQS should sit between S3 and Lambda because it gives the ingestion path:

- buffering during upload spikes
- retry behavior
- back-pressure control
- a DLQ path for failures

The repository already supports direct S3 events and SQS-wrapped S3 events. For production, the recommended path is:

```text
S3 -> SQS -> Lambda
```

### ECS Fargate for FastAPI

The FastAPI runtime is better deployed as a long-lived service in ECS Fargate because the app needs:

- authenticated API traffic
- dashboard and review workflows
- stable upload endpoints
- predictable health checks
- migration/bootstrap steps outside request handling

Forcing the whole API into Lambda would add complexity around cold starts, request size limits, runtime coordination, and operations. Lambda is still useful for the event-driven ETL job, but not as the primary hosting target for the product API.

### Mangum

Mangum should stay optional.

The repository already includes [app/lambda_handlers/api_handler.py](C:/Users/vitor/OneDrive/Documentos/Playground/app/lambda_handlers/api_handler.py), which exposes the FastAPI app through Lambda when needed. That is useful for experiments or edge deployments, but the recommended production path remains:

- FastAPI on ECS Fargate
- ETL ingestion on Lambda

This split keeps the app simpler and lowers operational risk.

## AWS Services Required

Minimum baseline:

- S3 bucket for raw portfolio files
- SQS queue for ingestion buffering
- SQS DLQ
- Lambda function for ETL ingestion
- RDS PostgreSQL
- ECS Fargate service for FastAPI
- ECR repository for backend container images
- S3 + CloudFront for frontend static hosting
- Secrets Manager or SSM Parameter Store for secrets
- CloudWatch Logs for API and Lambda logs

## Environment Variables

Use [.env.aws.example](C:/Users/vitor/OneDrive/Documentos/Playground/.env.aws.example) as the baseline.

Important values:

- `DATABASE_URL`
- `RAW_STORAGE_MODE=s3`
- `S3_BUCKET_NAME`
- `S3_BUCKET_PREFIX`
- `AWS_DEFAULT_REGION`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `ALERTS_ENABLED`
- `ALERT_PROVIDER`
- `ALERT_SNS_TOPIC_ARN`
- `AUTO_CREATE_TABLES=false`

Recommended secret handling:

- store `DATABASE_URL` in Secrets Manager or SSM SecureString
- store `JWT_SECRET_KEY` in Secrets Manager or SSM SecureString
- store `ALERT_SNS_TOPIC_ARN` in Parameter Store or config management if the topic is managed outside the app stack
- do not inject static AWS keys into ECS or Lambda if IAM roles are available

In AWS:

- ECS task role should access S3 as needed
- Lambda execution role should access S3, SQS, logs, and database networking

## Local-to-AWS Mapping

Current local stack:

- MinIO -> AWS S3
- Docker Compose PostgreSQL -> AWS RDS PostgreSQL
- local backend container -> ECS Fargate service
- local Lambda fixture tests -> real Lambda invocation from SQS/S3

This preserves the existing local workflow while keeping the production shape intuitive.

## Ingestion Flow in AWS

Recommended production flow:

1. A raw file lands in the S3 bucket.
2. S3 emits an object-created notification.
3. The notification is sent to SQS.
4. Lambda polls SQS and receives the wrapped S3 event.
5. [app.lambda_handlers.etl_handler](C:/Users/vitor/OneDrive/Documentos/Playground/app/lambda_handlers/etl_handler.py) parses the event.
6. [ETLService.run_from_lambda_invocation](C:/Users/vitor/OneDrive/Documentos/Playground/app/services/etl_service.py) routes processing to the real ETL pipeline.
7. The ETL downloads the object, processes it, loads PostgreSQL, and persists `ingestion_reports`.

Operationally useful metadata remains available:

- `source_type`
- `source_file`
- `raw_file`
- parser used
- confidence / review metadata
- processed rows / skipped rows

## Operational Alerts

CarteiraConsol is now prepared to emit first-line operational alerts for ingestion runs that require attention.

Current alert triggers:

- ingestion technical failure
- ingestion completed with `review_required=true`

Recommended production path:

- publish alerts to Amazon SNS
- subscribe operator email lists first
- add downstream channels later if needed

Why SNS first:

- simple and reliable
- email-friendly out of the box
- easy to fan out later to Lambda, HTTP, or incident tooling

Suggested production configuration:

- `ALERTS_ENABLED=true`
- `ALERT_PROVIDER=sns`
- `ALERT_SNS_TOPIC_ARN=arn:aws:sns:...`

Important behavior:

- alert delivery is best-effort
- SNS publish failures are logged
- ingestion success or failure is not blocked by alert delivery problems

Future extension point:

- WhatsApp or other operator channels can be added behind the same alert service without changing the ETL orchestration path

## SAM Baseline Included

The repository includes [template.yaml](C:/Users/vitor/OneDrive/Documentos/Playground/template.yaml) for the ingestion side only.

It defines:

- one Lambda function for ETL ingestion
- one SQS queue
- one DLQ
- one SQS event source mapping for Lambda
- an SQS queue policy that allows S3 to publish to the queue

What it intentionally does not attempt to model:

- full VPC/network stack
- RDS provisioning
- ECS service
- CloudFront distribution
- complete IAM organization

That keeps the artifact small and understandable.

## Wiring S3 to SQS

The SAM template creates the queue and queue policy, but you still need to configure the bucket notification so the S3 bucket sends object-created events to the queue.

Example AWS CLI shape:

```bash
aws s3api put-bucket-notification-configuration \
  --bucket "$RAW_BUCKET" \
  --notification-configuration '{
    "QueueConfigurations": [
      {
        "QueueArn": "arn:aws:sqs:us-east-1:123456789012:carteiraconsol-ingestion-queue",
        "Events": ["s3:ObjectCreated:*"],
        "Filter": {
          "Key": {
            "FilterRules": [
              { "Name": "prefix", "Value": "incoming/" }
            ]
          }
        }
      }
    ]
  }'
```

## FastAPI Deployment Recommendation

First production target:

- package the backend with the existing [Dockerfile](C:/Users/vitor/OneDrive/Documentos/Playground/Dockerfile)
- push the image to ECR
- run the API on ECS Fargate behind an ALB

Recommended runtime behavior:

- startup command:
  - `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`
- health check:
  - `GET /health`
- keep `AUTO_CREATE_TABLES=false`

Recommended ECS health strategy:

- ALB health check path: `/health`
- container health check can remain lightweight
- at least two tasks in production if cost allows

## Frontend Deployment Recommendation

First production target:

- build the React app with `npm run build`
- deploy static assets to S3
- front with CloudFront

The frontend should point to the deployed FastAPI API base URL.

In practice, use:

- a build-time environment variable for the API origin
- or a reverse-proxy path if you front both under the same domain

Recommended shape:

```text
app.example.com        -> CloudFront / static frontend
api.example.com        -> ALB -> ECS Fargate FastAPI
```

## Deployment Order

Recommended order for the first AWS rollout:

1. Provision S3 bucket, SQS queue, DLQ, and Lambda ingestion baseline.
2. Provision RDS PostgreSQL.
3. Prepare secrets in Secrets Manager or Parameter Store.
4. Build and push the backend container image to ECR.
5. Deploy the ECS Fargate API service.
6. Run database migrations with `alembic upgrade head`.
7. Create the first admin user with [scripts/create_admin.py](C:/Users/vitor/OneDrive/Documentos/Playground/scripts/create_admin.py).
8. Build and deploy the frontend static app.
9. Configure frontend API origin.
10. Wire S3 notifications to SQS and validate Lambda ingestion.

## Bootstrap and Migration Order

Production-safe order:

1. `AUTO_CREATE_TABLES=false`
2. `alembic upgrade head`
3. create the first admin user
4. release frontend traffic
5. enable ingestion events

This avoids schema drift and prevents the API from relying on implicit table creation.

## Admin Bootstrap

After the API has database access and migrations are applied:

```bash
python scripts/create_admin.py --email admin@example.com --full-name "Platform Admin"
```

Run this from:

- an ECS one-off task
- a CI/CD admin job
- or a controlled container shell during bootstrap

## Local Invocation and Demo Support

The repository already includes local invocation support for the Lambda ingestion path:

- [scripts/invoke_lambda_etl.py](C:/Users/vitor/OneDrive/Documentos/Playground/scripts/invoke_lambda_etl.py)
- [tests/fixtures/lambda_s3_event.json](C:/Users/vitor/OneDrive/Documentos/Playground/tests/fixtures/lambda_s3_event.json)
- [tests/fixtures/lambda_sqs_s3_event.json](C:/Users/vitor/OneDrive/Documentos/Playground/tests/fixtures/lambda_sqs_s3_event.json)

Examples:

```bash
python scripts/invoke_lambda_etl.py --s3-key "incoming/sample_portfolio.csv"
python scripts/invoke_lambda_etl.py --s3-event-key "incoming/sample_portfolio.csv"
python scripts/invoke_lambda_etl.py --sqs-event-key "incoming/sample_portfolio.csv"
```

## What Remains for a Later Phase

Useful future additions, but intentionally not included now:

- Terraform or CDK for the full stack
- VPC/subnet/security-group blueprints
- ECS service/task definition automation
- DLQ replay tooling
- CloudWatch alarms and operational alerts
- X-Ray/tracing dashboards
- blue/green deployment workflow

This baseline is designed to be the smallest credible path from the current repository to a real AWS deployment.
