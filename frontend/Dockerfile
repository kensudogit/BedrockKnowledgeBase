FROM node:20-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ENV PORT=3010
EXPOSE 3010
CMD ["npm", "run", "dev"]
