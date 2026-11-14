# Project: SPHEREx Sky Viewer (NASA Space Apps Challenge)

## Goal

A public web tool where a user enters sky coordinates (RA, Dec) and sees
a series of SPHEREx images of that patch played like a short video, so
moving or changing objects are easy to spot.

## Must-have features

- Input RA/Dec
- Fetch SPHEREx image cutouts for that position from different dates
- Display them as an animation (play/pause, frame slider)
- Works for: Barnard's Star, Epsilon Indi B, WISE 0855
  (RA 08h55m10.831s, Dec -07d14m42.53s), RW Aurigae, R Draconis

## Nice-to-have

- Coordinates in the URL (shareable/embeddable)
- Adjustable field of view
- Add/subtract images (difference imaging)
- Spectra, Gaia/WISE overlays, contamination flags

## Tech stack

- Python 3.13, FastAPI backend, astropy, numpy, pillow, astroquery, pyvo
- Simple HTML + JavaScript frontend
- Windows, virtual environment in /venv

## Rules for the AI

- I am a beginner. Explain what you did in simple terms.
- Keep code simple and well commented.
- Work in small steps. Tell me how to test each step.
- Do not rewrite files I didn't ask about.
- Ask me before installing new libraries.
- Keep data loading separate from display so real data can replace mock data easily.
