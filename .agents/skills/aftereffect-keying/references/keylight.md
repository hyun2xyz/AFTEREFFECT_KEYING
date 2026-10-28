# Keylight in After Effects: measured rounds, multipass and the viewer check

Use this on a Mac (CorridorKey's open-source build needs NVIDIA CUDA) or whenever the student keys in
AE. Settings come from Keylight 1.2's own guide: pick the screen colour, judge with **Status** and
**Screen Matte**, then Clip Black/White, then Clip Rollback/Softness, garbage outside, spill last.
The scripts turn that order into rounds you can repeat: every round is a script, a receipt, rendered
check frames and numbers measured from the source plate. The student's [rules](../../../../docs/rules.md)
and [AE comp guide](../../../../docs/ae-comp.md) (section 5) are the Korean versions.

## Commands

```sh
python -B scripts/keylight.py plan     --shot <shot>        # screen colour + garbage polygon -> shot.json, plan.png
python -B scripts/ae_comp.py  keylight --shot <shot> --fps <fps> [--background <file>]
python -B scripts/keylight.py run      work/<shot>/ae/build_comp.jsx   # or the student runs it in AE
python -B scripts/keylight.py round    --shot <shot> [--core on] [--set edge.clip_black=20 ...]
python -B scripts/keylight.py run      work/<shot>/keylight/round_NN/round.jsx
python -B scripts/keylight.py analyze  --shot <shot>        # report.json + sheet.png, hints
```

`plan` and `analyze` need NumPy/OpenCV (the `.venv` from `setup_environment.py --install`). `run` sends the script to the running AE
(macOS `osascript ... DoScriptFile`; Windows `--afterfx <AfterFX.exe>` with `-r`) and waits for the
receipt whose `job_id` matches; it deletes a stale receipt first. The build script refuses a project
that already has items; the round script changes only the listed parameters, renders with
`comp.saveFrameToPng`, restores every view and switch, and never saves, closes or renders.

## What the comp holds

`Plate` carries, in order: **Keylight Core** (off), **Keylight Edge**, **Key Cleaner** (off),
**Spill** (Advanced Spill Suppressor, Ultra, on). A shape layer **Garbage Matte** is the plate's
alpha track matte. Do not use Keylight's Outside Mask for the garbage: it left a thin line of
partial alpha along the mask edge inside the screen, and Outside Mask Softness made it worse.

- Screen Balance 50 for green, 95 for blue (Keylight's guide). Screen colour is the median of
  clearly-screen pixels between the 25th and 90th luminance percentile, not the brightest patch.
- Garbage polygon: non-screen regions joined to the frame border in every sampled frame, pulled
  `max(4, h/72)` px into the screen so the edge crosses clean screen, not the shadowed seam by a
  flag. `plan` warns only when the polygon cuts the subject; then use `--subject-touches bottom`
  or a smaller `--margin`.
- Spill key colour is the **pure hue** (0,1,0 or 0,0,1). With the measured, greyer screen colour
  the suppressor only partly acts (tinted soft edge on the test plate: off 1.2–2.3%, measured
  colour 0.6–1.5%, pure green 0%).

## Gates (per frame, from the source plate only)

| Metric | Pixels | Gate |
| --- | --- | --- |
| `bg_leak` | clearly-screen pixels, eroded and kept `max(4, h/120)` px from the subject, alpha > 2/255 | ≤ 0.05% |
| `garbage_leak` | outside the garbage polygon, alpha > 2/255 | ≤ 0.05% |
| `garbage_seam` | band just inside the polygon, away from the subject | ≤ 0.05% |
| `core_holes` | clearly-subject pixels eroded by the same distance, alpha < 253/255 | ≤ 0.05% |

"Clearly screen" means normalised screen excess > 0.25 **and** the screen channel at least 25% of
the screen colour's; near-black clothes read as pure green by the ratio alone. Reported, not
gated: soft-edge share in the band, and spill (share of soft-edge and solid pixels whose keyed
colour still leans to the screen; a truly green subject counts too). Numbers do not judge hair,
motion blur or flicker: look at `sheet.png` (plate | Status | key over checker | comp | core | zoom)
and play the comp.

## Order of rounds

1. Round 1 with defaults. Expect a veil on the screen and holes in dark or spill-lit areas.
2. Single pass: raise `edge.clip_black` in 5s until Status stays black; lower `edge.clip_white`
   in 5s (not much below 70) until the inside is solid. Leaks along rigs or the border are
   garbage work, not Clip Black.
3. If the inside only closes with hard clipping (soft-edge share drops well below round 1's),
   go multipass: `--core on --set edge.clip_white=100`. The core pass (clip 30/60, shrink
   `-max(2, h/240)`, View Intermediate Result) feeds the edge pass as **Source Alpha = Add To
   Inside Mask**, so the edge pass keeps soft edges and the eroded core keeps the inside solid.
4. Keep spill on; read the spill numbers; check skin and white props stay neutral.
5. Key Cleaner stays off unless the edge chatters in playback; it softens edges.

Test plate (1280×720, 180 frames, dark subject on an uneven green, AE 26.5 macOS, rounds
reproduced from a fresh build): defaults FAIL (veil on 46% of the screen, holes up to 4.8%);
single pass `clip_black 20 / clip_white 85` PASS with soft-edge share 0.61–0.70; multipass
`edge clip_black 20 / clip_white 100` + core PASS, holes 0 (min alpha 1.000), screen max ≤ 0.124
on isolated pixels, soft-edge share 0.82–0.87, spill 0%.

## Look at AE itself (computer use)

Rendered check frames are the evidence; the AE viewer is the second look, with the student when possible.
Switch the edge pass to Status (View 9) or Final Result (View 11) with a one-line script, set
`comp.time`, then capture the AE window and zoom into the subject.

- The viewer does not repaint while a modal dialog is open (for example the Run Script File
  panel) or while the window sits on another Space; the time readout moves but the picture stays.
  Close the dialog first. The Open panel is a separate process: never drive it with scripting;
  a background click does not reach it either. Ask the student, or with full-screen control press
  Escape after one click on the panel's toolbar (an overlay app such as KeyCastr may cover its
  buttons).
- Status: black = alpha 0, white = 1, grey = partial. Grey specks on the screen are leaks; a grey
  outline around the subject is the soft edge.

## Pitfalls seen

- `saveFrameToPng` in a **32 bpc** project (an EXR key) writes a 16-bit PNG whose colour channels
  hold value/10 (alpha unscaled; AE 26.5). Multiply colour by 10 before comparing. Keylight comps
  are 16 bpc.
- A symlinked frame folder imports the whole sequence from the link target; copy the frames.
- A comp named twice stops the round script; rebuild in a new empty project.
