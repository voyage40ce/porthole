# porthole

Lightweight local proxy manager for routing dev traffic across multiple microservices without Docker Compose overhead.

---

## Installation

```bash
pip install porthole
```

Or install from source:

```bash
git clone https://github.com/yourname/porthole.git && cd porthole && pip install -e .
```

---

## Usage

Define your services in a `porthole.yaml` file:

```yaml
services:
  api:
    port: 8001
    target: http://localhost:3001
  auth:
    port: 8002
    target: http://localhost:3002
  frontend:
    port: 8080
    target: http://localhost:5173
```

Then start the proxy manager:

```bash
porthole start
```

All configured routes will be live instantly. You can also start a single service:

```bash
porthole start --service api
```

Check the status of running proxies:

```bash
porthole status
```

Stop everything cleanly:

```bash
porthole stop
```

---

## Why porthole?

- **No Docker required** — runs directly against your local processes
- **Zero config boilerplate** — one YAML file, one command
- **Hot reload** — detects changes to `porthole.yaml` and re-routes automatically
- **Lightweight** — minimal dependencies, fast startup

---

## License

MIT © [yourname](https://github.com/yourname)