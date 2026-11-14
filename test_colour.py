# test_colour.py
# Tests the colour picture (Backend 21): processing.colour_picture().
#
# Parts 1-3 need nothing:                 python test_colour.py
# Part 4 needs the mock files:            python data_mock.py   (once)
# Part 4 is skipped if the mock files are missing.

import io
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image

import processing

MOCK_FILE = Path(__file__).parent / "data" / "mock" / "mock_00.fits"

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


def fails(func, *args, **kwargs):
    """True if the call raises a ValueError. Prints the message."""
    try:
        func(*args, **kwargs)
    except ValueError as err:
        print(f"        message: {err}")
        return True
    print("        NO ERROR RAISED")
    return False


SIZE = 50


def ramp(scale=1.0, size=SIZE):
    """An image that rises from 0 to 100*scale from left to right."""
    return np.tile(np.linspace(0.0, 100.0 * scale, size), (size, 1))


def fake(wave, image, day=0):
    return {"image": image, "wavelength_um": wave, "detector": 1,
            "obs_time": datetime(2026, 1, 1) + timedelta(days=day), "source_file": f"w{wave}"}


# Wavelengths are NOT in order, to prove the picking sorts them
frames = [fake(2.0, ramp(1.0)), fake(5.0, ramp(0.5)), fake(1.0, ramp(2.0)),
          fake(3.0, ramp(1.5)), fake(4.0, ramp(0.8))]

print("--- Part 1: choosing the three frames ---")
red, green, blue = processing.pick_colour_frames(frames)
print(f"   red = frame {red}, green = frame {green}, blue = frame {blue}")
check("red is the longest wavelength (5.0 um = frame 1)", red == 1)
check("blue is the shortest wavelength (1.0 um = frame 2)", blue == 2)
check("green is the middle one (3.0 um = frame 3)", green == 3)
check("exactly 3 frames: all three are used", sorted(processing.pick_colour_frames(frames[:3])) == [0, 1, 2])
check("fewer than 3 frames is refused", fails(processing.pick_colour_frames, frames[:2]))
check("no frames is refused", fails(processing.pick_colour_frames, []))
same = [fake(2.0, ramp()) for _ in range(4)]
check("all frames with one wavelength is refused", fails(processing.pick_colour_frames, same))

print("\n--- Part 2: colour_picture ---")
rgb = processing.colour_picture(frames)
check("shape is (height, width, 3)", rgb.shape == (SIZE, SIZE, 3))
check("dtype is uint8", rgb.dtype == np.uint8)
check("red channel = the stretched longest-wavelength frame",
      np.array_equal(rgb[:, :, 0], processing.stretch_image(frames[1]["image"])))
check("green channel = the stretched middle frame",
      np.array_equal(rgb[:, :, 1], processing.stretch_image(frames[3]["image"])))
check("blue channel = the stretched shortest-wavelength frame",
      np.array_equal(rgb[:, :, 2], processing.stretch_image(frames[2]["image"])))
own = processing.colour_picture(frames, channels=(0, 1, 2))
check("channels=(0,1,2) uses frames 0, 1, 2 as red, green, blue",
      np.array_equal(own[:, :, 0], processing.stretch_image(frames[0]["image"]))
      and np.array_equal(own[:, :, 2], processing.stretch_image(frames[2]["image"])))
check("channels may be a list", processing.colour_picture(frames, channels=[0, 1, 2]).shape == (SIZE, SIZE, 3))
check("a different stretch changes the picture",
      not np.array_equal(processing.colour_picture(frames, mode="linear"), processing.colour_picture(frames, mode="log")))

# Same shape, but frame B is twice as bright as frame A
a, b, c = fake(1.0, ramp(1.0)), fake(2.0, ramp(2.0)), fake(3.0, ramp(1.0))
own_scale = processing.colour_picture([a, b, c], mode="linear", shared_scale=False)
shared = processing.colour_picture([a, b, c], mode="linear", shared_scale=True)
check("own scale: every channel reaches the same brightness",
      own_scale[0, -1, 0] == own_scale[0, -1, 1])
check("shared scale: the brighter frame stays brighter than the others",
      shared[0, 20, 1] > shared[0, 20, 0] and shared[0, 20, 1] > shared[0, 20, 2])
check("original frames are not changed", np.array_equal(frames[0]["image"], ramp(1.0)))

nan_frames = [fake(1.0, ramp()), fake(2.0, ramp()), fake(3.0, ramp())]
nan_frames[1]["image"] = nan_frames[1]["image"].copy()
nan_frames[1]["image"][4, 4] = np.nan
check("NaN pixels are black in their channel",
      processing.colour_picture(nan_frames)[4, 4, 1] == 0)

print("\n--- Part 3: bad input and the PNG ---")
check("unknown stretch is refused", fails(processing.colour_picture, frames, None, "banana"))
check("channels with 2 numbers is refused", fails(processing.colour_picture, frames, (0, 1)))
check("channels outside the list is refused", fails(processing.colour_picture, frames, (0, 1, 9)))
check("channels with a negative number is refused", fails(processing.colour_picture, frames, (0, 1, -1)))
check("channels with text is refused", fails(processing.colour_picture, frames, (0, 1, "2")))
check("frames of different sizes are refused",
      fails(processing.colour_picture, [fake(1.0, ramp()), fake(2.0, ramp()), fake(3.0, ramp(size=30))]))
check("fewer than 3 frames is refused (automatic choice)", fails(processing.colour_picture, frames[:2]))
check("a grey array is refused by rgb_to_png_bytes",
      fails(processing.rgb_to_png_bytes, np.zeros((10, 10), dtype=np.uint8)))

# A 5x5 bright block, only in the RED frame, at pixel (10, 5) (y counted from the bottom)
def block_frame(wave, bright):
    img = np.zeros((SIZE, SIZE))
    if bright:
        img[3:8, 8:13] = 100.0
    return fake(wave, img)

trio = [block_frame(1.0, False), block_frame(2.0, False), block_frame(3.0, True)]   # longest = red
tri_rgb = processing.colour_picture(trio, mode="linear")
check("the block is pure red in the array", tuple(tri_rgb[5, 10]) == (255, 0, 0))
png_bytes = processing.rgb_to_png_bytes(tri_rgb)
png = Image.open(io.BytesIO(png_bytes))
check("the PNG is an RGB picture", png.mode == "RGB")
check("the PNG is enlarged 8 times (400 // 50)", png.size == (400, 400))
px, py = processing.pixel_to_png_position(10, 5, SIZE, SIZE)
pixels = np.array(png)
check("the PNG is pure red at the position from pixel_to_png_position (north is up)",
      tuple(pixels[int(py), int(px)]) == (255, 0, 0))
check("and black a little way off", tuple(pixels[int(py), int(px) + 80]) == (0, 0, 0))

print("\n--- Part 4: on the mock data ---")
if not MOCK_FILE.exists():
    print("SKIPPED  no mock files. Run:  python data_mock.py")
else:
    from astropy.io import fits
    import data_mock

    header = fits.getheader(MOCK_FILE)
    RA, DEC = header["CRVAL1"], header["CRVAL2"]
    mock = data_mock.get_frames(RA, DEC, 6.0)
    check("12 mock frames", len(mock) == 12)
    r, g, b = processing.pick_colour_frames(mock)
    print(f"   red = frame {r} ({mock[r]['wavelength_um']:.2f} um), green = frame {g} "
          f"({mock[g]['wavelength_um']:.2f} um), blue = frame {b} ({mock[b]['wavelength_um']:.2f} um)")
    check("mock: red = frame 11 (longest), blue = frame 0 (shortest)", r == 11 and b == 0)
    mrgb = processing.colour_picture(mock)
    check("mock: picture has 3 colour channels", mrgb.ndim == 3 and mrgb.shape[2] == 3)
    # Where is the moving dot in each of the 3 frames? (found on the RAW frames by
    # find_moving_dot from Backend 20; the stretched picture has many pure-white
    # pixels, so "the brightest pixel" would be a tie and not the dot.)
    trail = processing.find_moving_dot(mock)
    spots = []
    for name, idx in (("red", r), ("green", g), ("blue", b)):
        spots.append((name, idx, int(round(trail[idx]["y"])), int(round(trail[idx]["x"]))))
    print("   dot (y, x) in the red, green, blue frames:", [(y, x) for _n, _i, y, x in spots])
    check("the dot was found in the 3 chosen frames", all(trail[i]["found"] for i in (r, g, b)))
    check("the dot is in a different place in each colour frame (3 separate dots)",
          len({(y, x) for _n, _i, y, x in spots}) == 3)
    for k, (name, idx, y, x) in enumerate(spots):
        others = [c for c in range(3) if c != k]
        check(f"at the {name} dot the {name} channel is bright and the other two are dim",
              mrgb[y, x, k] > 200 and all(mrgb[y, x, c] < 150 for c in others))
    out = Path(__file__).parent / "cache" / "test_png"
    out.mkdir(parents=True, exist_ok=True)
    (out / "colour_mock.png").write_bytes(processing.rgb_to_png_bytes(mrgb))
    print("   saved", out / "colour_mock.png", "(open it and look at it)")

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")