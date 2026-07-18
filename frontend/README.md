# Kanban Studio

## Run

```bash
npm install
npm run dev
```

## Tests

```bash
npm run test:unit
npm run lint
npm run build
```

End-to-end tests run against the container-served production build:

```bash
../scripts/start-mac.sh
npm run test:e2e
../scripts/stop-mac.sh
```
