# Étape 1 : build de l'app React (Vite)
FROM node:20-slim AS build
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Vite intègre les variables VITE_* directement dans le JS au moment du
# build — pas au runtime. Il faut donc connaître l'URL du backend AVANT
# de builder, contrairement à une variable d'environnement classique.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Étape 2 : servir les fichiers statiques générés avec nginx (léger, pas
# besoin de Node.js qui tourne en permanence pour du contenu statique)
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
