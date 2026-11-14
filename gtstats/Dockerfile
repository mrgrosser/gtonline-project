FROM node:22-alpine
WORKDIR /app
COPY --chown=node:node server.mjs ./
COPY --chown=node:node public ./public
USER node
ENV PORT=3000 DATA_FILE=/data/stats.json
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s CMD node -e "fetch('http://127.0.0.1:3000/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node","server.mjs"]
