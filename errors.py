# errors.py
# Backend 14: the wording of error messages, in one place.
#
# main.py uses these so that EVERY error the API sends looks the same:
#     {"detail": "A sentence a person can read."}
# The web page can then show "detail" directly.
#
# This file only builds text. It needs no web server and no astropy,
# so it is easy to test (see test_errors.py).

# Shown when something unexpected crashes inside the server (HTTP 500).
# The technical details go to the terminal, never to the visitor.
SERVER_ERROR_MESSAGE = (
    "Something went wrong on the server. Please try again in a moment. "
    "If it keeps happening, try a different position or a smaller field of view."
)

# Shown when the data source takes too long (HTTP 504).
TIMEOUT_MESSAGE = (
    "The data source took too long to answer. Please try again in a moment, "
    "or try a smaller field of view."
)


def no_images_message(ra_deg, dec_deg, using_mock):
    """Text for 'no images cover this position' (HTTP 404)."""
    text = (f"No images cover RA {ra_deg:.4f}, Dec {dec_deg:+.4f} degrees. "
            f"Try another position or a larger field of view.")
    if using_mock:
        text += " (Practice mode: the fake data only covers the patch around WISE 0855.)"
    return text


def validation_message(errors):
    """Turn FastAPI's technical validation errors into one friendly sentence.

    errors: the list from RequestValidationError.errors(). Each item is a
            dictionary with (at least) "loc" (where the problem is, such as
            ("query", "ra")) and "type" (such as "missing").
    Only the first problem is reported.
    """
    if not errors:
        return "Something in the web address is not valid."
    first = errors[0]
    loc = first.get("loc") or ()
    name = str(loc[-1]) if loc else "value"

    if first.get("type") == "missing":
        if name in ("ra", "dec"):
            return "Please give both ra and dec, for example ra=133.8&dec=-7.2."
        return f"The setting '{name}' is missing."
    if name == "index":
        return "The frame number must be a whole number, for example 0."
    return f"The value given for '{name}' is not valid."


# Stock wording from the web framework, replaced by friendlier text.
_GENERIC_HTTP_TEXT = {
    404: ("Not Found", "There is nothing at this address. Check the web address for typing mistakes."),
    405: ("Method Not Allowed", "This address does not accept that kind of request."),
}


def friendly_http_detail(status_code, detail):
    """Replace the framework's stock wording; keep our own messages unchanged."""
    stock = _GENERIC_HTTP_TEXT.get(status_code)
    if stock is not None and detail == stock[0]:
        return stock[1]
    return detail