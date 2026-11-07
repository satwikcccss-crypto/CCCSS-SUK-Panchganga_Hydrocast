# =============================================================================
# HydroCast Panchganga — Frontend Dockerfile (Next.js Public Portal)
# Port 3000
# =============================================================================

FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
