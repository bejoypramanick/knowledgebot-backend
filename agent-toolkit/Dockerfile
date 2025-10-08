# Multi-stage Dockerfile for OpenAI AgentToolkit Lambda Functions
FROM public.ecr.aws/lambda/python:3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TRANSFORMERS_CACHE=/tmp/transformers_cache
ENV HF_HOME=/tmp/huggingface_cache
ENV HF_DATASETS_CACHE=/tmp/huggingface_datasets_cache
ENV TORCH_HOME=/tmp/torch_cache
ENV SENTENCE_TRANSFORMERS_HOME=/tmp/sentence_transformers_cache
ENV DOCLING_ARTIFACTS_PATH=/tmp/docling_artifacts

# Set default embedding configuration (can be overridden by Lambda environment variables)
ENV EMBEDDING_TYPE=local
ENV EMBEDDING_MODEL=all-MiniLM-L6-v2

# Install system dependencies
RUN yum update -y && \
    yum install -y \
    gcc \
    gcc-c++ \
    make \
    cmake \
    git \
    wget \
    curl \
    unzip \
    libffi-devel \
    openssl-devel \
    libjpeg-devel \
    libpng-devel \
    libtiff-devel \
    freetype-devel \
    lcms2-devel \
    libwebp-devel \
    tcl-devel \
    tk-devel \
    libxml2-devel \
    libxslt-devel \
    zlib-devel \
    bzip2-devel \
    readline-devel \
    sqlite-devel \
    xz-devel \
    expat-devel \
    gdbm-devel \
    ncurses-devel \
    libuuid-devel \
    libffi-devel \
    && yum clean all

# Create cache directories
RUN mkdir -p /tmp/transformers_cache \
    /tmp/huggingface_cache \
    /tmp/huggingface_datasets_cache \
    /tmp/torch_cache \
    /tmp/sentence_transformers_cache \
    /tmp/docling_artifacts

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download and cache models
RUN python -c "\
import os; \
os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'; \
os.environ['HF_HOME'] = '/tmp/huggingface_cache'; \
os.environ['HF_DATASETS_CACHE'] = '/tmp/huggingface_datasets_cache'; \
os.environ['TORCH_HOME'] = '/tmp/torch_cache'; \
os.environ['SENTENCE_TRANSFORMERS_HOME'] = '/tmp/sentence_transformers_cache'; \
from sentence_transformers import SentenceTransformer; \
model = SentenceTransformer('all-MiniLM-L6-v2'); \
print('Sentence transformer model downloaded and cached'); \
try: \
    from docling.document_converter import DocumentConverter; \
    from docling.datamodel.base_models import InputFormat; \
    from docling.datamodel.pipeline_options import PdfPipelineOptions; \
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfPipelineOptions(do_ocr=True, do_table_structure=True, table_structure_options={'do_cell_matching': True})}); \
    print('Docling models downloaded and cached'); \
except Exception as e: \
    print(f'Docling model download failed: {e}'); \
"

# Copy application code
COPY crud_operations.py ${LAMBDA_TASK_ROOT}/
COPY lambda_handlers.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD ["lambda_handlers.lambda_handler"]
