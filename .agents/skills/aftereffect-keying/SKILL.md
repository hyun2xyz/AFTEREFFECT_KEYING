---
name: aftereffect-keying
description: Set up a clean Windows/macOS computer and teach green/blue screen keying with CorridorKey 2.0 (installed by the student from the official repository, NVIDIA GPU) or After Effects Keylight, alpha diagnostics and a Python-generated After Effects composite, while following the CorridorKey and footage licenses. Use in this repository for a student's shot; no AE MCP.
---

# Aftereffect Keying

This is a repository-bound teaching skill. Run from the repository root that
contains `scripts/setup_environment.py`. Rules live in
[rules](../../../docs/rules.md); lesson order in [workflow](../../../docs/workflow.md).

## First interaction

1. Inspect the actual OS/shell, GPU and repository root. If tools are missing,
   start with [START-HERE](../../../START-HERE.md) and read only the matching setup:
   [Windows](../../../docs/setup-windows.md) or [macOS](../../../docs/setup-macos.md).
2. Run `setup_environment.py --check`. CorridorKey's public Python release needs
   an NVIDIA RTX 30-series or newer GPU; otherwise use After Effects Keylight.
   On a Mac never install it or download its weights. Tell the student plainly
   that CorridorKey on a Mac means buying the official paid app/plugin
   (corridorkey.com; M-series, macOS 14+, no Intel Macs; beta in October 2026)
   and that Keylight needs no purchase. Purchase, install and the activation key
   are the student's; this repository has not tested the paid version. Its
   Premultiplied output is not straight alpha: for `scripts/ae_comp.py --key`,
   merge Straight FG with Matte into straight RGBA first
   ([macOS setup](../../../docs/setup-macos.md)).
3. Before installing CorridorKey, summarize its license from rules section 1 and
   install it only from the official repository into a separate folder and venv.
4. Locate the student's clip and create `work/<shot>`. Keep the original intact.
   Explain the next step in two or three sentences, then do only that step.

## License rules

- Never copy CorridorKey code, weights, its venv or the foundation-model weights
  into this repository, a lesson bundle or a student deliverable.
- Do not offer CorridorKey as a paid service or put it behind paid access. Any
  released modification must be free, under the same license and keep the name.
- Practice plates from Hollywood Camera Work are for local practice: do not
  re-host them or publish direct download links; link only the source page.
- Record the source and license of every background plate.

## Keying rules

- Record FPS, stored resolution, pixel aspect ratio and color space in
  `shot.json`. Do not resize before keying.
- Start with a short no-hint run (default despill 0.5, outputs alpha fg checker
  cutout). Use a first-frame hint matte only when subject selection is wrong.
- Remove rigs and stands with garbage masks, not by pushing keyer settings.
- Keylight in AE (no NVIDIA GPU, or a Mac): tune in measured rounds with
  `scripts/keylight.py` (plan, round, run, analyze), go multipass when the
  inside only closes with hard clipping, keep spill suppression on the pure
  screen hue. Method and gates: [Keylight rounds](references/keylight.md).
- CorridorKey's best-quality alpha for AE is the float EXR cutout
  (`--outputs alpha cutout --output_format exr --exr_dtype float`); an EXR key
  makes the `keying` comp 32 bpc, sRGB IEC61966-2.1, linear blending.
- Review on black, white and checker at start/middle/end and the busiest
  frames; measure background-only alpha (should be 0) and solid-subject alpha
  (near 1) over every frame and call them diagnostics without a ground-truth
  matte. Play the result to check edge flicker. Fully decode every output.
- In AE interpret alpha as Straight with the correct pixel aspect ratio and
  FPS; do not double-convert sRGB/linear. Keep key, background, contact shadow
  and grade as separate editable layers. Check the last frame of the final file.
- Build the AE project with `scripts/ae_comp.py keying|keylight` ([ae-comp](../../../docs/ae-comp.md)):
  it writes JSX the student runs in a new, empty project through
  File > Scripts > Run Script File (or `keylight.py run` sends it to the running
  AE); then read `build_comp.result.json` with the printed `job_id`, or let the
  student import manually. No MCP,
  persistent bridge, overwrite of open projects, automatic save or render.
- A composite that does not look convincing is a failure even when technical
  checks pass.

## Context and long work

Run CorridorKey in the background with its own venv, one clip at a time; read
`processing.log` and short JSON summaries instead of long logs. After each lesson
write `work/<shot>/next.md`: files, what was verified, visible problems, one next step.

## Growing the skill

Move a step into `scripts/` only after it worked on a real shot. Keep shot values
in `shot.json`. Add new failure patterns and fixes to `docs/rules.md` with the shot
they came from.
