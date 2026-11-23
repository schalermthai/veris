# Veris skills

Agent skills for building and running a project's verification system.

| Skill | Version | Purpose |
|---|---|---|
| [veris-verification-bootstrap](skills/veris-verification-bootstrap) | 1.2 | Bootstrap, harden, or validate the verification environment and shared runtime |
| [veris-story-verifier](skills/veris-story-verifier) | 1.0 | Independently verify user stories on the real surface |
| [veris-regression-author](skills/veris-regression-author) | 1.0 | Turn verified stories into permanent E2E regression cases |
| [veris-regression-selector](skills/veris-regression-selector) | 1.0 | Select the regression cases a change affects |
| [veris-regression-runner](skills/veris-regression-runner) | 1.0 | Execute selected regression cases against the runtime |
| [veris-verification-auditor](skills/veris-verification-auditor) | 1.0 | Audit the reliability of the whole verification system |

## Install

Copy or symlink a skill folder into `~/.claude/skills/` (personal) or `.claude/skills/` (project):

```sh
ln -s "$PWD/skills/veris-story-verifier" ~/.claude/skills/veris-story-verifier
```
