# Use a lightweight Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application code
COPY app.py .

# Expose the port Streamlit uses by default
EXPOSE 8501

# Command to run the Streamlit app
CMD["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]