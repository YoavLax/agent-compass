# Commercial licensing

AI Readiness Analyzer (AgentCompass) is licensed under the
[PolyForm Noncommercial License 1.0.0](LICENSE). That license permits any
noncommercial purpose and nothing else.

If what you want to do is commercial, you need a separate written license
from both copyright holders. This page tells you whether you need one and
how to ask.

## You do not need a commercial license to

- read the source, run it locally, or evaluate it
- use it for personal study, research, experiment, or a hobby project
- use it inside a charity, school, university, public research body, public
  health or safety body, environmental organisation, or government
  institution — the license covers these regardless of how they are funded
- fork it, modify it, and publish your changes for any of the above
- open issues and pull requests here

Contributions are welcome and stay welcome. Nothing on this page restricts
participation in the project.

## You do need a commercial license to

- run it inside a for-profit company, on that company's repositories,
  including internally and including as a CI step
- offer it, or anything built on it, as a paid or ad-supported product or
  service
- resell it, bundle it into a commercial product, or host it for customers
- use its output as part of a paid consulting or audit deliverable

If your use is somewhere between the two lists, ask. A short description of
what you want to do is enough for us to answer.

## How to ask

Open an issue titled `commercial license` at
<https://github.com/YoavLax/agent-compass/issues>, or email the maintainers
listed in [`pyproject.toml`](pyproject.toml).

Tell us:

1. who is using it (organisation and rough size)
2. what you want to do with it — internal use, embedded in a product,
   offered as a service
3. whether you need to modify it, and whether those modifications would be
   published

We will come back with terms. Small teams, startups pre-revenue, and
maintainers of open-source projects should say so — that changes the answer.

## Versions released under MIT

Every commit up to and including `a592f6ca0536b3e396e7fa4df42d2f97f2227e59`
was published under the MIT License and stays available under it, commercial
use included. That grant is preserved in [`LICENSE-MIT`](LICENSE-MIT) and is
not revoked by this change. Only later versions carry the noncommercial
terms.

## Third-party code

Portions of `src/airx/config.py` and `src/airx/rules/skills.py` originate in
[AgentEval](https://github.com/YoavLax/AgentEval) under the MIT License, and
carry their own permissions. See [`NOTICE`](NOTICE).
