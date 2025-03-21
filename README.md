# TISControlProtocol

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Version 0.5.14](https://img.shields.io/badge/version-0.5.14-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11+-orange)
![signed](https://img.shields.io/badge/signed-yes-green)

TISControlProtocol is a powerful Python package for controlling TIS devices. It provides a simple and intuitive API for interacting with TIS devices, making it easy to integrate TIS devices into your Python applications.

## Features

- ✅ Fully Supports Asynchronous Operations
- ✅ Flawless feedback mechanism to prevent data loss
- ✅ Debounce mechanism to prevent multiple commands from being sent for protection
- ✅ Easy to use API for controlling TIS devices
- ✅ Clean and simple codebase
- ✅ Ready to integrate with Home Assistant

## Installation

You can install TISControlProtocol by adding it to your Manifest file or by using pip. Here's how you can install it using pip:

```bash
pip install TISControlProtocol
```

## Verifying Package Signatures

This package is signed with GPG to ensure authenticity. Follow these steps to verify:

1. **Install GPG**: Ensure you have GPG installed (`gpg --version`).
2. **Get My Public Key**:
   - Import from a keyserver: `gpg --keyserver hkp://keyserver.ubuntu.com --recv-keys 97DADF7C6008FBCEB93506624A93BA55D2B45649`
   - Import it: `gpg --import mykey.pub`
3. **Download Files**: Get the `.tar.gz`, `.whl`, and `.asc` files from PyPI or GitHub Releases.
4. **Verify**:
   ```bash
   gpg --verify tiscontrolprotocol-0.5.14.tar.gz.asc tiscontrolprotocol-0.5.14.tar.gz
   gpg --verify tiscontrolprotocol-0.5.14-py3-none-any.whl.asc tiscontrolprotocol-0.5.14-py3-none-any.whl
## License

TISControlProtocol is licensed under the MIT license. See the [LICENSE](https://your-license-link) file for details.
