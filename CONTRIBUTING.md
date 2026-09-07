# Contributing to JWProtect Self-Hosted

Thanks for considering a contribution. This is a small, self-hosted image
attribution and watermark verification project — contributions of any
size are welcome, including documentation fixes and issue reports.

## Before you start

- For anything beyond a small fix, please open an issue first describing
  what you want to change and why. This avoids wasted work if the
  direction doesn't fit the roadmap.
- Check existing issues and the [Roadmap](./ROADMAP.md) to see if
  something similar is already planned or being discussed.

## Local setup

```bash
git clone https://github.com/Jingwei-Protect/jingwei-selfhost.git
cd jingwei-selfhost
cp .env.example .env
docker compose up --build
```

The app is served on `http://localhost:8080` once the containers are up.
For backend-only work without Docker, see the Python requirements in
`requirements.txt` (and `requirements-adv.txt` only if you're working on
the optional AdvProtect module).

## Running tests

```bash
pytest
```

Please add or update tests for any behavior change under `tests/`.

## Pull requests

- Keep PRs focused on one change; unrelated fixes should be separate PRs.
- Describe what changed and why in the PR description.
- Make sure `pytest` passes locally before opening the PR.
- Documentation-only PRs (README, docs/, this file) don't need tests.

## Code style

- Match the existing style in the file you're editing rather than
  introducing a new formatting convention.
- Avoid adding new dependencies for small changes; ask first in an issue
  if you think a new dependency is necessary.

## Reporting bugs

Open an issue with:

- What you expected to happen.
- What actually happened.
- Steps to reproduce, including whether you're running via Docker Compose
  or a local Python environment.
- Relevant logs (please remove any personal data first).

## Security issues

Do not open a public issue for security vulnerabilities. See
[SECURITY.md](./SECURITY.md) instead.

## License

By contributing, you agree that your contributions will be licensed under
this project's [MIT License](./LICENSE). Do not submit sample images or
other assets unless you have the rights to license them under
[SAMPLES-LICENSE.md](./SAMPLES-LICENSE.md).
