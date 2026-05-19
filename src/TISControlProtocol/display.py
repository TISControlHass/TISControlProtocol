import logging
import os
import time
from PIL import Image, ImageDraw, ImageFont

try:
    import fcntl
    import struct
    import glob
    import gpiod
    from gpiod.line import Direction, Value

    HAS_ST7789 = True
except (ImportError, RuntimeError) as e:
    HAS_ST7789 = False
    logging.error(
        "Failed to load display dependencies. Display will be disabled. Error: %s", e
    )


class TISDisplay:
    def __init__(self, display_logo: str, version: str):
        self.display_logo = display_logo
        self.version = version
        self.spi_fd = None
        self.chip_path = None
        self.req_dc = None
        self.req_rst = None
        self.global_req_blk = None
        self.chip0 = None

    def _set_pin(self, pin, value):
        try:
            val = Value.ACTIVE if value else Value.INACTIVE
            if pin == 23:
                self.req_dc.set_value(23, val)
            elif pin == 25:
                self.req_rst.set_value(25, val)
        except Exception as e:
            logging.error(f"Error setting pin {pin} to {value}: {e}")

    def send_command(self, cmd):
        self._set_pin(23, 0)  # Command mode (0)
        os.write(self.spi_fd, bytes([cmd]))

    def send_data(self, data):
        self._set_pin(23, 1)  # Data mode (1)
        if isinstance(data, int):
            os.write(self.spi_fd, bytes([data]))
        else:
            os.write(self.spi_fd, bytes(data))

    def init_display(self):
        # Hardware Reset
        self._set_pin(25, 1)
        time.sleep(0.1)
        self._set_pin(25, 0)
        time.sleep(0.1)
        self._set_pin(25, 1)
        time.sleep(0.1)

        # ST7789 Initialization Sequence
        self.send_command(0x01)  # SWRESET
        time.sleep(0.15)
        self.send_command(0x11)  # Sleep out
        time.sleep(0.15)

        self.send_command(0x3A)  # Color mode 16-bit
        self.send_data(0x55)  # 0x55 for RGB565

        self.send_command(0x36)  # Memory Access Control (MADCTL)
        self.send_data(0x00)  # Normal rotation

        self.send_command(0x21)  # INVON
        self.send_command(0x13)  # NORON
        time.sleep(0.01)
        self.send_command(0x29)  # Display on
        time.sleep(0.1)

    def set_window(self, x1, y1, x2, y2):
        self.send_command(0x2A)  # Column Address Set
        self.send_data(bytearray([x1 >> 8, x1 & 0xFF, x2 >> 8, x2 & 0xFF]))

        self.send_command(0x2B)  # Row Address Set
        self.send_data(bytearray([y1 >> 8, y1 & 0xFF, y2 >> 8, y2 & 0xFF]))
        self.send_command(0x2C)  # RAMWR

    def set_display_image(self):
        if self.display_logo:
            img = Image.open(self.display_logo).convert("RGB")
            version_text = f"V {self.version}"

            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.load_default(size=28)
            except TypeError:
                font = ImageFont.load_default()

            x, y = 78, 235
            draw.text((x, y), version_text, font=font, fill=(255, 255, 255))
            img = img.rotate(180, expand=True)

            if img.size != (240, 320):
                img = img.resize((240, 320))

            r, g, b = img.split()
            r_data = (
                list(r.getdata())
                if not hasattr(r, "get_flattened_data")
                else r.get_flattened_data()
            )
            g_data = (
                list(g.getdata())
                if not hasattr(g, "get_flattened_data")
                else g.get_flattened_data()
            )
            b_data = (
                list(b.getdata())
                if not hasattr(b, "get_flattened_data")
                else b.get_flattened_data()
            )

            rgb565 = bytearray(img.width * img.height * 2)
            for i in range(len(r_data)):
                pixel = (
                    ((r_data[i] & 0xF8) << 8)
                    | ((g_data[i] & 0xFC) << 3)
                    | (b_data[i] >> 3)
                )
                rgb565[i * 2] = pixel >> 8
                rgb565[i * 2 + 1] = pixel & 0xFF

            self.set_window(0, 0, img.width - 1, img.height - 1)
            self._set_pin(23, 1)  # Data mode

            mv = memoryview(rgb565)
            chunk_size = 4096
            for i in range(0, len(mv), chunk_size):
                os.write(self.spi_fd, mv[i : i + chunk_size])

    def run_display(self):
        try:
            if HAS_ST7789:
                # Initialize SPI Bus natively
                self.spi_fd = os.open("/dev/spidev0.0", os.O_RDWR)
                SPI_IOC_WR_MODE = 0x40016B01
                SPI_IOC_WR_MAX_SPEED_HZ = 0x40046B04
                fcntl.ioctl(self.spi_fd, SPI_IOC_WR_MODE, struct.pack("B", 0))
                fcntl.ioctl(
                    self.spi_fd, SPI_IOC_WR_MAX_SPEED_HZ, struct.pack("I", 10000000)
                )

                # Initialize GPIOs via gpiod dynamically
                self.chip_path = None
                chip_paths = glob.glob("/dev/gpiochip*")
                for chip_path in chip_paths:
                    try:
                        with gpiod.Chip(chip_path) as chip:
                            info = chip.get_info()
                            if info.num_lines >= 50 or "bcm" in info.label.lower():
                                self.chip_path = chip_path
                                break
                    except Exception:
                        pass

                if not self.chip_path:
                    logging.error("Could not find a suitable BCM gpiochip!")
                    return

                self.req_dc = gpiod.request_lines(
                    self.chip_path,
                    consumer="display_dc",
                    config={
                        23: gpiod.LineSettings(
                            direction=Direction.OUTPUT, output_value=Value.INACTIVE
                        )
                    },
                )
                self.req_rst = gpiod.request_lines(
                    self.chip_path,
                    consumer="display_rst",
                    config={
                        25: gpiod.LineSettings(
                            direction=Direction.OUTPUT, output_value=Value.INACTIVE
                        )
                    },
                )

                try:
                    self.chip0 = gpiod.Chip("/dev/gpiochip0")
                    self.global_req_blk = self.chip0.request_lines(
                        config={12: gpiod.LineSettings(direction=Direction.OUTPUT)}
                    )
                    self.global_req_blk.set_value(12, Value.INACTIVE)
                except Exception as e:
                    logging.error(f"Failed to initialize global backlight: {e}")

                self.init_display()
                self.set_display_image()
            else:
                logging.error("Can't start display, some packages are missing")

        except Exception as e:
            logging.error(f"error initializing display, {e}")
            return
