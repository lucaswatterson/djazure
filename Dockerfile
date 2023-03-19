# Use Python 3.11 Base Image
FROM --platform=linux/amd64 python:3.11

# Install Microsoft ODBC 17.
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql17
RUN apt-get install -y unixodbc-dev

# Upgrade Pip
RUN python3.11 -m pip install --upgrade pip

# Install Python Dependencies
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Python Container Best Practices
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy Project Code
WORKDIR /app
COPY . /app

# Expose Port 8000
EXPOSE 8000

# Create a non-root user with an explicit UID and adds permission to access the /app folder.
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Start Gunicorn
CMD ["gunicorn", "--worker-tmp-dir", "/dev/shm", "--workers=2", "--threads=4", "--worker-class=gthread", "--log-file=-", "djazure.wsgi:application", "--bind", "0.0.0.0:8000"]
