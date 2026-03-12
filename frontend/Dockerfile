# Stage 1: Build the React application
FROM node:20-slim AS build

WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:alpine

# Copy the build output from the first stage to nginx's serve directory
COPY --from=build /app/dist /usr/share/nginx/html

# Copy a custom nginx configuration to handle SPA routing if necessary
# If you don't have one, the default Nginx config works for simple cases, 
# but for SPA it's better to have one that redirects 404s to index.html.

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
