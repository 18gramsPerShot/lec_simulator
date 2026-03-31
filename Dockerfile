# Use a lightweight Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application code
COPY web_ui.py .

# Expose the port Streamlit uses by default
EXPOSE 8501

# Command to run the Streamlit app
CMD["streamlit", "run", "web_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]