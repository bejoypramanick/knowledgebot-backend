FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.9

# Copy function code
COPY lambda/chat-handler.py ${LAMBDA_TASK_ROOT}/
COPY config.py ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install --no-cache-dir \
    boto3 \
    pydantic \
    anthropic \
    numpy \
    annotated-types \
    typing-extensions \
    typing-inspection \
    six

# Set the CMD to your handler
CMD [ "chat-handler.lambda_handler" ]
