# AFTEREFFECT_KEYING — classroom starter

Read `.agents/skills/aftereffect-keying/SKILL.md` for this repository's workflow
and `docs/rules.md` for the keying and license rules. For a computer without
prerequisites, start with `START-HERE.md` and only the current OS setup. Do not
attempt Python commands before locating Python. This repository is the source of
its project skill; do not install or change global agent rules.

- Teach one next step at a time. Inspect the student's actual footage, GPU and
  installed tools before choosing commands. Preserve student edits and originals.
- Summarize the CorridorKey license before installing it. Install CorridorKey only
  from its official repository into a separate folder and venv. Never copy its
  code, weights or venv into this repository or a deliverable.
- Do not re-host practice plates or publish their direct download links.
- Use Python and generated JSX for AE, never an AE MCP server or a new bridge.
- The student works in their own fork: `origin` is the fork, `upstream` is
  `hyun2xyz/AFTEREFFECT_KEYING`. Follow `docs/fork-and-update.md`. Update with
  `git fetch upstream` + `git merge upstream/main`; never reset, force-push or
  discard the student's commits. Before a commit, check `git status` and stop if
  footage, AEP, generated media, weights or `tools.local.json` would be included.
- Codex asks for approval before network commands (git, gh, pip, brew, winget)
  and writes outside this folder. Request it and explain why; never change
  sandbox or security settings to avoid it.
- Keep footage, outputs and AEP files in ignored `work/` or a student-selected
  folder. Never commit private data, weights or app binaries.
- Sampled visual checks and alpha diagnostics are not ground-truth accuracy.
- Add a script only after it worked on a real shot. Keep shot values in
  `work/<shot>/shot.json`, not in code.
