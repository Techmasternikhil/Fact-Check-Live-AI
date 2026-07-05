# Use the official Node.js 20 slim image
FROM node:20-slim

# Create app directory
WORKDIR /usr/src/app

# We don't have a package.json since we used a global install or standard modules,
# but if there were dependencies, we would copy them here.
# For our setup, we install express, rss-parser, and @modelcontextprotocol/sdk
RUN npm init -y && \
    npm install express rss-parser @modelcontextprotocol/sdk

# Copy application source code
COPY server.js .
COPY mcp-server.js .
COPY public/ ./public/

# Expose the application port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
# The backend URL will be injected via docker-compose or Cloud Run
ENV ADK_BACKEND_URL=http://backend:8000

# Start the Node.js Express server
CMD ["node", "server.js"]
