# Frame format

Each frame is a dictionary with:

- image: 2D numpy array (pixel values)
- wcs: astropy WCS object (pixel <-> sky conversion)
- obs_time: observation date/time (UTC)
- wavelength_um: band center in microns
- detector: detector number 1-6
- flags: 2D array of bad-pixel/contamination flags (or None)
- variance: 2D array of noise estimates (or None)
- source_file: where it came from

A data source function has this signature:
get_frames(ra_deg, dec_deg, fov_arcmin) -> list of frames sorted by obs_time
