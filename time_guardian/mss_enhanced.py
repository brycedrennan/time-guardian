"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from ctypes import POINTER, c_ubyte

import Quartz.CoreGraphics as CG
from mss.darwin import MSS as DarwinMSS, CGRect
from mss.exception import ScreenShotError
from mss.screenshot import ScreenShot, Size


class MSS(DarwinMSS):
    """Multiple ScreenShots implementation for macOS.
    It uses intensively the CoreGraphics library.
    """

    def _grab_impl(self, monitor, /) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGB."""
        core = self.core
        rect = CGRect((monitor["left"], monitor["top"]), (monitor["width"], monitor["height"]))
        imageOption = (
            CG.kCGWindowImageBoundsIgnoreFraming | CG.kCGWindowImageShouldBeOpaque | CG.kCGWindowImageNominalResolution
        )
        image_ref = core.CGWindowListCreateImage(rect, 1, 0, imageOption)
        if not image_ref:
            msg = "CoreGraphics.CGWindowListCreateImage() failed."
            raise ScreenShotError(msg)

        width = core.CGImageGetWidth(image_ref)
        height = core.CGImageGetHeight(image_ref)
        prov = copy_data = None
        try:
            prov = core.CGImageGetDataProvider(image_ref)
            copy_data = core.CGDataProviderCopyData(prov)
            data_ref = core.CFDataGetBytePtr(copy_data)
            buf_len = core.CFDataGetLength(copy_data)
            raw = ctypes.cast(data_ref, POINTER(c_ubyte * buf_len))
            data = bytearray(raw.contents)

            # Remove padding per row
            bytes_per_row = core.CGImageGetBytesPerRow(image_ref)
            bytes_per_pixel = core.CGImageGetBitsPerPixel(image_ref)
            bytes_per_pixel = (bytes_per_pixel + 7) // 8

            if bytes_per_pixel * width != bytes_per_row:
                cropped = bytearray()
                for row in range(height):
                    start = row * bytes_per_row
                    end = start + width * bytes_per_pixel
                    cropped.extend(data[start:end])
                data = cropped
        finally:
            if prov:
                core.CGDataProviderRelease(prov)
            if copy_data:
                core.CFRelease(copy_data)

        return self.cls_image(data, monitor, size=Size(width, height))
